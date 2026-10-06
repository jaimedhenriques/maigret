#!/usr/bin/env python3
"""Authenticated 21st CLI + streamable HTTP MCP; credentials never enter Git."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib.request import Request,urlopen


def token():
    value=os.environ.get('API_KEY_21ST') or os.environ.get('TWENTYFIRST_TOKEN')
    if not value:
        local=Path.home()/'.config/verisento/design-secrets.json'
        if local.exists():value=json.loads(local.read_text()).get('API_KEY_21ST')
    if not value:raise SystemExit('Set API_KEY_21ST or run 21st login; never commit credentials.')
    return value


def mcp(method,arguments=None):
    credential=token()
    headers={'x-api-key':credential,'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
    def request(method,params,id):
        payload={'jsonrpc':'2.0','id':id,'method':method,'params':params}
        with urlopen(Request('https://21st.dev/api/mcp',data=json.dumps(payload).encode(),headers=headers,method='POST'),timeout=30) as response:
            if response.headers.get('Mcp-Session-Id'):headers['Mcp-Session-Id']=response.headers['Mcp-Session-Id']
            body=response.read().decode()
            if body.lstrip().startswith('{'):return json.loads(body)
            return json.loads([line[6:] for line in body.splitlines() if line.startswith('data: ')][-1])
    request('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'verisento-design','version':'1.0'}},1)
    if method=='tools':result=request('tools/list',{},2)
    else:result=request('tools/call',{'name':method,'arguments':arguments or {}},2)
    print(json.dumps(result,indent=2).replace(credential,'[REDACTED]'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['tools','search','component','cli'])
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.action=='cli':
        credential=token();env=os.environ.copy();env.update({'API_KEY_21ST':credential,'TWENTYFIRST_TOKEN':credential,'NODE_USE_ENV_PROXY':'1'})
        result=subprocess.run(['21st',*args.arguments],env=env,capture_output=True,text=True)
        print((result.stdout+result.stderr).replace(credential,'[REDACTED]'));raise SystemExit(result.returncode)
    elif args.action=='tools':mcp('tools')
    elif args.action=='search':mcp('search',{'query':' '.join(args.arguments),'type':'component','limit':5})
    else:
        if len(args.arguments)!=1:parser.error('component requires one numeric demo ID')
        mcp('get_component',{'id':int(args.arguments[0])})

if __name__=='__main__':main()
