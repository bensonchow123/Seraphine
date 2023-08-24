from googleapiclient import discovery
from dotenv import load_dotenv
import os
load_dotenv()
async def perspective_api(chat_data):
    attributes_thresholds = {
        'SEVERE_TOXICITY': 0.8,
        'INSULT': 0.8,
        'SEXUALLY_EXPLICIT': 0.8,
        'IDENTITY_ATTACK': 0.8,
        # 'THREAT': 0.8,
        'PROFANITY': 0.8
    }


    requested_attributes = {}

    for key in attributes_thresholds:
        requested_attributes[key] = {}

    client = discovery.build(
        "commentanalyzer",
        "v1alpha1",
        developerKey=os.getenv("GoogleDeveloperKey"),
        discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
    )

    analyze_request = {
        'comment': {'text': str(chat_data)},
        'requestedAttributes': requested_attributes,
        "languages":"en"
    }

    response = client.comments().analyze(body=analyze_request).execute()
    if response:
        data = {}
        for key in response['attributeScores']:
            data[key] = [True, round(response['attributeScores'][key]['summaryScore']['value']*100,2)] if response['attributeScores'][key]['summaryScore']['value'] >= attributes_thresholds[key] else [False]
        return data


