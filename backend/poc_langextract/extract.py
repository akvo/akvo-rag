import pprint
import langextract as lx
import textwrap


from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings


loader = PyPDFLoader(
    "./Agricultural-Policy-2021.pdf_Agricultural_Policy_2021_f42afc885f.pdf"
)
doc = loader.load()

# TODO:: We need to make the extraction prompt and examples depend to KB
# - each KB maybe have different metadata structure needed
# - this prompt and examples maybe can be implemented in the FE when iniate KB
# -

# 1. Define the prompt and extraction rules
prompt = textwrap.dedent(
    """\
    Extract these specific fields from the document:
    1. title: The document title of filename (e.g., "AGRICULTURAL POLICY - 2021")
    2. topic: The document topic (e.g., "Agricultural", "Water", etc.),
    3. region: The document reporting regions or country (e.g., "Kenya"),
    4. publication_date: The date of document reported
    5. deprecated_items: Things marked as deprecated
    """
)

# 2. Provide a high-quality example to guide the model
examples = [
    lx.data.ExampleData(
        text="Ministry of Agriculture, \nLivestock , Fisheries\n and Cooperatives\niii\nThe major livestock resources include cattle, camel, poultry, sheep, goats, bees, emerging livestock and their \nproducts. These support livelihoods through provision of food and wealth for Kenyans and signiﬁcantly contribute   \nto   the   National economy.  The livestock sub-sector has the potential to provide adequate supply of all animal \nproducts to meet domestic needs and surplus for export. For growth in the livestock sub-sector , the policy recognizes \nthe need to improve animal genetics, control of trade sensitive diseases, value addition of livestock produce and \nincreased access to markets that greatly increase the industry's performance.\nFisheries are a major source of income, food, employment and foreign exchange earnings in Kenya. We have both \nnatural ﬁsheries resources in the fresh inland water bodies and the Indian Ocean as well as farmed ﬁsh from our \ngrowing aquaculture systems. Kenya's annual ﬁsh production is valued at approximately KES. 22 billion at ex-vessel \nprice. Inland capture ﬁsheries (fresh water) contributed 111,814 tonnes (83%) of ﬁsh valued at KES. 18.58 billion \nwhile marine capture ﬁsheries contributed 23,286 tonnes (17%) valued at KES. 4.38 billion (KNBS, 2018).",
        extractions=[
            lx.data.Extraction(
                extraction_class="title",
                extraction_text="Ministry of Agriculture, Livestock, Fisheries and Cooperatives",
                attributes={},
            ),
            lx.data.Extraction(
                extraction_class="topic",
                extraction_text="livestock resources",
                attributes={},
            ),
            lx.data.Extraction(
                extraction_class="region",
                extraction_text="Kenya",
                attributes={},
            ),
            lx.data.Extraction(
                extraction_class="publication_date",
                extraction_text="2018",
                attributes={},
            ),
        ],
    )
]

# The input text to be processed
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200
)
chunks = text_splitter.split_documents(doc)

extracted_docs = []
for chunk in chunks[:10]:
    pprint.pprint(chunk)
    input_text = chunk.page_content

    # Run the extraction
    result = lx.extract(
        text_or_documents=input_text,
        prompt_description=prompt,
        examples=examples,
        model_id="gpt-4o",
        api_key=settings.OPENAI_API_KEY,
        fence_output=True,
        use_schema_constraints=False,
    )

    metadata = {
        "title": "unknown",
        "topic": "unknown",
        "region": "unknown",
        "publication_date": 0,
        "deprecated": False,
    }

    for extraction in result.extractions:
        if extraction.extraction_class == "title":
            metadata["title"] = extraction.extraction_text
        elif extraction.extraction_class == "topic":
            metadata["topic"] = extraction.extraction_text
        elif extraction.extraction_class == "region":
            metadata["region"] = extraction.extraction_text
        elif extraction.extraction_class == "publication_date":
            metadata["publication_date"] == extraction.extraction_text
        elif extraction.extraction_class == "deprecated_items":
            metadata["deprecated"] = True

    extracted_docs.append(
        {"chunk_content": chunk.page_content, "metadata": metadata}
    )


pprint.pprint(extracted_docs)


"""
Example result:
✓ Extracted 3 entities (3 unique types)
  • Time: 1.29s
  • Speed: 733 chars/sec
  • Chunks: 1
[{'chunk_content': 'MINISTRY OF AGRICULTURE, LIVESTOCK,    \n'
                   'FISHERIES AND COOPERATIVES\n'
                   'AGRICULTURAL POLICY - 2021\n'
                   '   “FOOD: OUR HEALTH, WEALTH AND SECURITY” \n'
                   ' \n'
                   'REPUBLIC OF KENYA\n'
                   'MINISTRY OF AGRICULTURE, \n'
                   'LIVESTOCK, FISHERIES AND \n'
                   'COOPERATIVES\n'
                   '2021',
  'metadata': {'deprecated': True,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'AGRICULTURAL POLICY - 2021',
               'topic': 'Agricultural'}},
 {'chunk_content': 'MINISTRY OF AGRICULTURE, LIVESTOCK,    \n'
                   'FISHERIES AND COOPERATIVES\n'
                   ' “FOOD: OUR HEALTH, WEALTH AND SECURITY” \n'
                   ' AGRICULTURAL POLICY - 2021',
  'metadata': {'deprecated': True,
               'publication_date': 0,
               'region': 'Not specified',
               'title': 'AGRICULTURAL POLICY - 2021',
               'topic': 'Agricultural'}},
 {'chunk_content': 'Ministry of Agriculture, \n'
                   'Livestock , Fisheries\n'
                   ' and Cooperatives\n'
                   'i\n'
                   'FOREWORD\n'
                   'The Fourth Schedule of the Constitution of Kenya \n'
                   'provides for the Agricultural Policy as a function of \n'
                   'the National Government. It transfers key components \n'
                   'of agriculture including crop and animal husbandry, \n'
                   'ﬁsheries development and control of plant and animal \n'
                   'diseases amongst others to the County governments. \n'
                   'The Constitution also af ﬁrms the right of every person \n'
                   'to be free from hunger and to have food of acceptable \n'
                   'quality and quantity.\n'
                   'Agriculture forms the basis of food production in the \n'
                   'country and signiﬁcantly contributes to growth of the \n'
                   'national economy. National and County Governments \n'
                   'need to develop appropriate strategies that will \n'
                   'lead to food and nutrition security and safety at \n'
                   'their respective levels. The Ministry of Agriculture, \n'
                   'Livestock, Fisheries and Cooperatives, in collaboration \n'
                   'with County governments and relevant stakeholders,',
  'metadata': {'deprecated': False,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'Ministry of Agriculture, Livestock, Fisheries and '
                        'Cooperatives',
               'topic': 'Agricultural Policy'}},
 {'chunk_content': 'their respective levels. The Ministry of Agriculture, \n'
                   'Livestock, Fisheries and Cooperatives, in collaboration \n'
                   'with County governments and relevant stakeholders, \n'
                   'has taken the initiative to formulate the Agricultural \n'
                   'Policy which will be the basis of legislation, '
                   'strategies, \n'
                   'plans, projects and programmes for the country’s \n'
                   'agricultural development. Respective agriculture \n'
                   'commodity based and county agricultural policies and \n'
                   'legislations are expected to conform to the Agricultural \n'
                   'Policy.\n'
                   'The Policy has been formulated in line with relevant \n'
                   'provisions of the Constitution and provides a clear \n'
                   'road map to the realization of Vision 2030 agricultural \n'
                   'goals and targets. It identiﬁes current challenges in \n'
                   'the Agricultural Sector and outlines suitable guidelines \n'
                   'to address them. It provides measures towards sustain- \n'
                   'able use of natural resources, particularly land and \n'
                   'water , which are expected to boost agricultural \n'
                   'production and productivity.',
  'metadata': {'deprecated': False,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'Ministry of Agriculture, Livestock, Fisheries and '
                        'Cooperatives',
               'topic': 'Agricultural Policy'}},
 {'chunk_content': 'to address them. It provides measures towards sustain- \n'
                   'able use of natural resources, particularly land and \n'
                   'water , which are expected to boost agricultural \n'
                   'production and productivity.\n'
                   'In addressing the challenges, the Policy recognizes \n'
                   'institutional and capacity limitations in the '
                   'Agricultural \n'
                   'Sector and provides for functional linkages between \n'
                   'the Sector and respective institutions whose domains \n'
                   'have potential impacts on agricultural value chains. It \n'
                   'takes cognizance of cross-cutting issues, particularly \n'
                   'agriculture in a changing climate, youth and gender , \n'
                   'which have signiﬁcant effects on agricultural \n'
                   'development.\n'
                   'The Policy af ﬁrms the interrelationship between food \n'
                   'and health together with insecurity levels that have a \n'
                   'deﬁnite bearing on personal and national security. In \n'
                   'this regard, it emphasizes the need for National and \n'
                   'County Governments to commit adequate resources to \n'
                   'enable sustainable production of sufﬁcient and diverse',
  'metadata': {'deprecated': False,
               'publication_date': 0,
               'region': 'National',
               'title': 'unknown',
               'topic': 'Agricultural'}},
 {'chunk_content': 'this regard, it emphasizes the need for National and \n'
                   'County Governments to commit adequate resources to \n'
                   'enable sustainable production of sufﬁcient and diverse \n'
                   'nutrient dense foods. Consequently, the highest \n'
                   'leadership at both levels of government is expected \n'
                   'to take responsibility for the development of annual \n'
                   'implementation plans for this Policy.\n'
                   'Hon. Peter G. Munya, E.G.H.,\n'
                   'Cabinet Secretary, \n'
                   'Ministry of Agriculture Livestock Fisheries and \n'
                   'Cooperatives.',
  'metadata': {'deprecated': False,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'Annual Implementation Plans for Agricultural Policy',
               'topic': 'agricultural policy'}},
 {'chunk_content': 'Ministry of Agriculture, \n'
                   'Livestock , Fisheries\n'
                   ' and Cooperatives\n'
                   'ii\n'
                   'PREFACE\n'
                   'The Agricultural Sector continues to be a key economic \n'
                   'and social driver of development in Kenya’s Vision \n'
                   '2030 and Sustainable Development Goals (SDGs). The \n'
                   'Constitution of Kenya under the Bill of Rights provides \n'
                   'for the “right to food of adequate quality and quantity \n'
                   'at all times for all”. This right is a clear mandate and \n'
                   'requirement which must be given priority to ensure \n'
                   'food safety, food security and nutrition even as we \n'
                   'pursue other equally important objectives of reducing \n'
                   'poverty and generating employment. This Policy high- \n'
                   'lights the challenges, opportunities and proposes \n'
                   'interventions for sustainable development of crops, \n'
                   'livestock and ﬁsheries and sub-sectors.\n'
                   'With the current impacts of climate change and \n'
                   'emerging pests and diseases posing a great challenge \n'
                   'to agriculture production, the policy recognizes the \n'
                   'need for crop diversiﬁcation and irrigation to enhance',
  'metadata': {'deprecated': True,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'Ministry of Agriculture, Livestock, Fisheries and '
                        'Cooperatives',
               'topic': 'Agricultural Sector'}},
 {'chunk_content': 'emerging pests and diseases posing a great challenge \n'
                   'to agriculture production, the policy recognizes the \n'
                   'need for crop diversiﬁcation and irrigation to enhance \n'
                   'food production, household income, National wealth \n'
                   'and food & nutrition security.\n'
                   'Crops contribute greatly to the economy where the \n'
                   'industrial crops contribute upto 70% of agricultural \n'
                   'exports and these include tea, coffee, sugarcane, \n'
                   'cotton, sunﬂower , pyrethrum, barley, tobacco, sisal, \n'
                   'coconut and bixa. Tea is a leading foreign exchange \n'
                   'earner and its export value was KES 104.1 billion in \n'
                   '2019, KES 134.8 billion in 2018 and KES 134.8 billion \n'
                   'in 2017. In 2017 fresh horticultural crops contributed \n'
                   'export earning of KES 115.3 billion growing to KES 144.6 \n'
                   'billion in 2019, (KNBS, 2020). Food crops contribute \n'
                   'about 32% of the AgGDP and 0.5% of exports earning.\n'
                   'Livestock plays an important economic and socio-\n'
                   'cultural role among many Kenyan communities. The \n'
                   'sub-sector employs 50% of the agricultural labor force',
  'metadata': {'deprecated': True,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'None',
               'topic': 'agriculture production'}},
 {'chunk_content': 'Livestock plays an important economic and socio-\n'
                   'cultural role among many Kenyan communities. The \n'
                   'sub-sector employs 50% of the agricultural labor force \n'
                   'and over 10 million Kenyans living in the Arid and \n'
                   'Semi-Arid Lands (ASALs) derive their livelihood largely \n'
                   'from livestock. The value of livestock and livestock \n'
                   'products increased from KES 146.8 billion in 2018 to \n'
                   'KES 147.9 billion in 2019 (KNBS, 2020). About 60% of \n'
                   'Kenya’s livestock herd is found in the ASALs, which \n'
                   'constitute over 80% of the country.',
  'metadata': {'deprecated': True,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'None',
               'topic': 'livestock'}},
 {'chunk_content': 'Ministry of Agriculture, \n'
                   'Livestock , Fisheries\n'
                   ' and Cooperatives\n'
                   'iii\n'
                   'The major livestock resources include cattle, camel, '
                   'poultry, sheep, goats, bees, emerging livestock and '
                   'their \n'
                   'products. These support livelihoods through provision of '
                   'food and wealth for Kenyans and signiﬁcantly '
                   'contribute   \n'
                   'to   the   National economy.  The livestock sub-sector has '
                   'the potential to provide adequate supply of all animal \n'
                   'products to meet domestic needs and surplus for export. '
                   'For growth in the livestock sub-sector , the policy '
                   'recognizes \n'
                   'the need to improve animal genetics, control of trade '
                   'sensitive diseases, value addition of livestock produce '
                   'and \n'
                   'increased access to markets that greatly increase the '
                   'industry’s performance.\n'
                   'Fisheries are a major source of income, food, employment '
                   'and foreign exchange earnings in Kenya. We have both \n'
                   'natural ﬁsheries resources in the fresh inland water '
                   'bodies and the Indian Ocean as well as farmed ﬁsh from our',
  'metadata': {'deprecated': False,
               'publication_date': 0,
               'region': 'Kenya',
               'title': 'Ministry of Agriculture, Livestock, Fisheries and '
                        'Cooperatives',
               'topic': 'livestock resources'}}]
"""
