Stack: Streamlit and RAGAS
Goal: A system to evaluate RAG responses and then iterate on the settings that might effect quality

Build a utility to send a message to a chat for a given knowledge base based on the contents of backend/app/api/api_v1/chat.py 

Use the utility to generate responses in for RAGAs evaluation

For now, the docker containers must be up to execute - just assume they are in the command to start streamlit and the button 

Add logging which will only be produced when the evaluation is run throught streamlit

Design a way for this logging to be captured and displayed in the streamlit UI

instrument the code - the major steps - to generate this logging. It should give the part of the process the logging is happening from and the inputs and outputs of the instrumented step

Create a command to bring up the streamlit ui

For the configured knowledge bases (identified by label):

- Show all the prompts to be tested in streamlit
- Show a button to run the evaluation in streamlit
- Show the results of the evaluation in streamlit
- Show the logs collected throughout the run in streamlit

For now, assume the existence of a knowledge base labeled "Living Income Benchmark Knowledge Base"

For now, run against the local instance of Akvo RAG configured to run with `docker compose up`. Assume the existence of the knowledge bases targeted identifed by `label`. Assume `docker compose up` has been run to start the containers.

Build in `backend/RAG_evaluation/`

Install required dependencies in the backend container but clearly mark that these are only for the evaluation system and should not be used in production.

- Later we will find a way to isolate dev dependencies from production dependencies but I don't believe this repo currently implements this.

Add a readme explaining how to use the evaluation system such as ensuring the full system is running before execution, what script to execute, what knowledge bases are expected to be set up, configuration for the LLM API (assume the Open AI key - see how this is configured in the wider project)

