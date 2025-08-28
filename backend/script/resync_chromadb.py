#!/usr/bin/env python3
"""
Permanent ChromaDB Resync Script
Restores ChromaDB vector store from MySQL database chunks.

Usage:
  python3 resync_chromadb.py <kb_id>           # Resync specific KB
  python3 resync_chromadb.py --all             # Resync all KBs
  python3 resync_chromadb.py --check           # Check status of all KBs
"""
import sys
import argparse
import logging
import time
from typing import Dict, List

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_in_container():
    """Run the resync script inside the backend container"""
    import subprocess
    
    # Check if we're inside the container
    try:
        with open('/proc/1/cgroup', 'r') as f:
            if 'docker' not in f.read():
                # We're outside the container, copy and run inside
                print("🔄 Running resync inside backend container...")
                
                # Copy script to container
                subprocess.run([
                    'docker', 'cp', __file__, 'akvo-rag-backend-1:/tmp/resync_chromadb.py'
                ], check=True)
                
                # Run inside container with same arguments
                cmd = ['docker', 'exec', 'akvo-rag-backend-1', 'python', '/tmp/resync_chromadb.py'] + sys.argv[1:]
                result = subprocess.run(cmd)
                sys.exit(result.returncode)
    except:
        pass  # Assume we're already in container

def get_kb_status() -> Dict[int, Dict]:
    """Get status of all knowledge bases"""
    sys.path.append('/app')
    
    from app.db.session import SessionLocal
    from app.models.knowledge import KnowledgeBase, DocumentChunk
    from app.services.vector_store import VectorStoreFactory  
    from app.services.embedding.embedding_factory import EmbeddingsFactory
    from app.core.config import settings
    
    db = SessionLocal()
    status = {}
    
    try:
        # Get all KBs
        kbs = db.query(KnowledgeBase).all()
        
        for kb in kbs:
            # Get MySQL chunk count
            mysql_count = db.query(DocumentChunk).filter(DocumentChunk.kb_id == kb.id).count()
            
            # Get ChromaDB count
            chroma_count = 0
            try:
                embeddings = EmbeddingsFactory.create()
                vector_store = VectorStoreFactory.create(
                    store_type=settings.VECTOR_STORE_TYPE,
                    collection_name=f"kb_{kb.id}",
                    embedding_function=embeddings,
                )
                chroma_count = vector_store._store._collection.count()
            except Exception as e:
                logger.warning(f"Failed to check ChromaDB for KB {kb.id}: {e}")
            
            needs_sync = mysql_count > 0 and chroma_count != mysql_count
            
            status[kb.id] = {
                'name': kb.name,
                'mysql_chunks': mysql_count,
                'chroma_chunks': chroma_count,
                'needs_sync': needs_sync,
                'status': 'OK' if not needs_sync else 'NEEDS_SYNC'
            }
    
    finally:
        db.close()
    
    return status

def resync_kb(kb_id: int, batch_size: int = 100) -> bool:
    """Resync a specific knowledge base"""
    sys.path.append('/app')
    
    from app.db.session import SessionLocal
    from app.models.knowledge import DocumentChunk, KnowledgeBase
    from app.services.vector_store import VectorStoreFactory
    from app.services.embedding.embedding_factory import EmbeddingsFactory
    from app.core.config import settings
    from langchain_core.documents import Document as LangchainDocument
    
    print(f"🔄 Starting resync for KB {kb_id}...")
    
    db = SessionLocal()
    
    try:
        # Get KB info
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            print(f"❌ Knowledge base {kb_id} not found!")
            return False
        
        print(f"📚 KB: {kb.name}")
        
        # Count chunks
        total_chunks = db.query(DocumentChunk).filter(DocumentChunk.kb_id == kb_id).count()
        if total_chunks == 0:
            print(f"⚠️  No chunks found in MySQL for KB {kb_id}")
            return True
        
        print(f"📊 MySQL chunks: {total_chunks}")
        
        # Create vector store
        embeddings = EmbeddingsFactory.create()
        vector_store = VectorStoreFactory.create(
            store_type=settings.VECTOR_STORE_TYPE,
            collection_name=f"kb_{kb_id}",
            embedding_function=embeddings,
        )
        
        # Check current state
        current_count = vector_store._store._collection.count()
        print(f"📈 Current ChromaDB count: {current_count}")
        
        if current_count == total_chunks:
            print("✅ Already in sync!")
            return True
        
        # Process chunks
        processed_count = current_count
        start_time = time.time()
        
        print(f"🚀 Adding {total_chunks - current_count} chunks in batches of {batch_size}...")
        
        offset = current_count
        batch_num = 0
        
        while offset < total_chunks:
            batch_num += 1
            
            # Get batch
            chunk_batch = (db.query(DocumentChunk)
                          .filter(DocumentChunk.kb_id == kb_id)
                          .offset(offset)
                          .limit(batch_size)
                          .all())
            
            if not chunk_batch:
                break
            
            # Convert to Langchain docs
            langchain_docs = []
            for chunk_data in chunk_batch:
                page_content = chunk_data.chunk_metadata.get('page_content', '')
                if page_content:
                    langchain_doc = LangchainDocument(
                        page_content=page_content,
                        metadata=chunk_data.chunk_metadata.copy()
                    )
                    langchain_docs.append(langchain_doc)
            
            # Add to vector store
            if langchain_docs:
                vector_store.add_documents(langchain_docs)
                processed_count += len(langchain_docs)
                
                # Progress
                progress_pct = processed_count / total_chunks * 100
                elapsed = time.time() - start_time
                rate = (processed_count - current_count) / elapsed if elapsed > 0 else 0
                
                print(f"  📦 Batch {batch_num}: {processed_count}/{total_chunks} ({progress_pct:.1f}%) - {rate:.1f} chunks/sec")
            
            offset += batch_size
        
        # Final check
        final_count = vector_store._store._collection.count()
        print(f"✅ Resync completed! ChromaDB now has {final_count} chunks")
        
        return True
        
    except Exception as e:
        print(f"❌ Resync failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Main function with CLI"""
    
    # If not in container, run in container
    run_in_container()
    
    parser = argparse.ArgumentParser(description='ChromaDB Resync Tool')
    parser.add_argument('kb_id', nargs='?', help='Knowledge base ID to resync')
    parser.add_argument('--all', action='store_true', help='Resync all KBs that need it')
    parser.add_argument('--check', action='store_true', help='Check status of all KBs')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    
    args = parser.parse_args()
    
    print("🔄 ChromaDB Resync Tool")
    print("=" * 40)
    
    if args.check:
        print("📊 Checking status of all knowledge bases...\n")
        status = get_kb_status()
        
        print(f"{'KB ID':<6} {'Status':<12} {'MySQL':<8} {'ChromaDB':<10} {'Name'}")
        print("-" * 70)
        
        needs_sync_kbs = []
        for kb_id, info in status.items():
            status_icon = "⚠️" if info['needs_sync'] else "✅"
            print(f"{kb_id:<6} {status_icon} {info['status']:<10} {info['mysql_chunks']:<8} {info['chroma_chunks']:<10} {info['name'][:40]}")
            if info['needs_sync']:
                needs_sync_kbs.append(kb_id)
        
        if needs_sync_kbs:
            print(f"\n💡 To resync: python3 resync_chromadb.py --all")
            print(f"   Or individually: python3 resync_chromadb.py <kb_id>")
        else:
            print("\n🎉 All knowledge bases are in sync!")
    
    elif args.all:
        print("🔄 Resyncing all knowledge bases that need it...\n")
        status = get_kb_status()
        needs_sync = [kb_id for kb_id, info in status.items() if info['needs_sync']]
        
        if not needs_sync:
            print("✅ All knowledge bases already in sync!")
            return
        
        print(f"Found {len(needs_sync)} KBs that need syncing: {needs_sync}")
        success_count = 0
        
        for kb_id in needs_sync:
            print(f"\n{'='*50}")
            if resync_kb(kb_id, args.batch_size):
                success_count += 1
        
        print(f"\n🎉 Completed! {success_count}/{len(needs_sync)} KBs successfully synced")
    
    elif args.kb_id:
        try:
            kb_id = int(args.kb_id)
            success = resync_kb(kb_id, args.batch_size)
            if success:
                print("\n🎉 Resync successful!")
            else:
                print("\n💥 Resync failed!")
                sys.exit(1)
        except ValueError:
            print("❌ Invalid KB ID. Must be a number.")
            sys.exit(1)
    
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python3 resync_chromadb.py --check        # Check all KBs")
        print("  python3 resync_chromadb.py 15             # Resync KB 15")
        print("  python3 resync_chromadb.py --all          # Resync all that need it")

if __name__ == "__main__":
    main()