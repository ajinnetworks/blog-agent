from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(override=True)
token = os.environ.get('GITHUB_TOKEN', 'NOT FOUND')
print('토큰길이:', len(token))
g = Github(auth=Auth.Token(token))
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')
print('연결 성공:', repo.full_name)
