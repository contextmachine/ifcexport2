import json
import os

import dotenv

dotenv.load_dotenv(".env")
VIEWER_URL = os.environ.get("VIEWER_URL", "http://localhost:3000")
VIEWER_GRAPHQL_BACKEND_URL = URL = f'{VIEWER_URL}{os.environ.get("VIEWER_GRAPHQL_BACKEND_URL", "/api/graphql")}'
VIEWER_USER_ID = USER_ID = os.environ.get("VIEWER_USER_ID", "4f648824-f38c-4990-9c6a-e88935b7e5af")
VIEWER_GRAPHQL_BACKEND_HEADERS=HEADERS = json.loads(os.environ.get("VIEWER_GRAPHQL_BACKEND_HEADERS", '{"Content-Type":"application/json"}'))


AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_BUCKET= os.environ.get("AWS_DEFAULT_BUCKET")
AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME", 'ru-central1')
AWS_ENDPOINT_URL=os.environ.get('AWS_ENDPOINT_URL', 'http://storage.yandexcloud.net')

CXM_USE_SSL=bool(int(os.getenv('CXM_USE_SSL', 0)))
