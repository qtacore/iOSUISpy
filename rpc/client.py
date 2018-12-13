# -*- coding:utf-8 -*-
#
# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this 
# file except in compliance with the License. You may obtain a copy of the License at
# 
# https://opensource.org/licenses/BSD-3-Clause
# 
# Unless required by applicable law or agreed to in writing, software distributed 
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#
'''RPC Framework
'''

import json
import random
import string
import SimpleXMLRPCServer
import xmlrpclib
try:
    import fcntl
except ImportError:
    fcntl = None

IDCHARS = string.ascii_lowercase+string.digits

def random_id(length=8):
    return_id = ''
    for _ in range(length):
        return_id += random.choice(IDCHARS)
    return return_id

class RPCClientProxy(object):
    '''RPC Client
    '''

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 allow_none=0, use_datetime=0, context=None):
        # establish a "logical" server connection

        if isinstance(uri, unicode):
            uri = uri.encode('ISO-8859-1')

        # get the url
        import urllib
        protocol, uri = urllib.splittype(uri)
        if protocol not in ("http", "https"):
            raise IOError, "unsupported JSON-RPC protocol"
        self.__host, self.__handler = urllib.splithost(uri)
        if not self.__handler:
            self.__handler = "/RPC2"

        if transport is None:
            if protocol == "https":
                transport = SafeTransport(use_datetime=use_datetime, context=context)
            else:
                transport = Transport(use_datetime=use_datetime)
        self.__transport = transport

        self.__encoding = encoding
        self.__verbose = verbose
        self.__allow_none = allow_none

    def __close(self):
        self.__transport.close()

    def __request(self, methodname, params):
        # call a method on the remote server
        request = {"jsonrpc": "2.0"}
        if len(params) > 0:
            request["params"] = params
        request["id"] = random_id()
        request["method"] = methodname
        request = json.dumps(request)
        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose
            )
        response = json.loads(response)
        if not isinstance(response, dict):
            raise TypeError('Response is not dict')
        if 'error' in response.keys() and response['error'] is not None:
            raise DriverApiError(response['error']['message'])
        else:
            response = response['result'][0]
            if isinstance(response, dict):
                return self.encode_dict(response, "UTF-8")
            elif isinstance(response, list):
                return self.encode_list(response, "UTF-8")
            elif isinstance(response, unicode):
                return response.encode("UTF-8")
            return response

    def __repr__(self):
        return (
            "<ServerProxy for %s%s>" %
            (self.__host, self.__handler)
            )

    __str__ = __repr__

    def __getattr__(self, name):
        # magic method dispatcher
        return xmlrpclib._Method(self.__request, name)

    # note: to call a remote object with an non-standard name, use
    # result getattr(server, "strange-python-name")(args)

    def __call__(self, attr):
        """A workaround to get special attributes on the ServerProxy
           without interfering with the magic __getattr__
        """
        if attr == "close":
            return self.__close
        elif attr == "transport":
            return self.__transport
        raise AttributeError("Attribute %r not found" % (attr,))
    
            
    def encode_dict(self, content, encoding="UTF-8"):
        '''将字典编码为指定形式
        
        :param content: 要编码内容
        :type content: dict
        :param encoding:编码类型
        :type encoding: str
        :returns: dict -- 编码后的字典
        '''
        for key in content:
            if isinstance(content[key], dict):
                content[key] = self.encode_dict(content[key], encoding)
            elif isinstance(content[key], unicode):
                content[key] = content[key].encode(encoding)
            elif isinstance(content[key], list):
                content[key] = self.encode_list(content[key], encoding)
        return content   
    
    def encode_list(self, content, encoding="UTF-8"):
        '''将列表编码为指定形式
        
        :param content: 要编码内容
        :type content: list
        :param encoding:编码类型
        :type encoding: str
        :returns: list -- 编码后的列表
        '''
        for ind, item in enumerate(content):
            if isinstance(item, dict):
                content[ind] = self.encode_dict(item, encoding)
            elif isinstance(item, unicode):
                content[ind] = content[ind].encode(encoding)
            elif isinstance(item, list):
                content[ind] = self.encode_list(item, encoding)
        return content


class DriverApiError(Exception):
    '''Driver API Error
    '''

class Fault(object):
    '''JSON-RPC Error
    '''

    def __init__(self, code=-12306, message = None, rpcid=None):
        self.faultCode = code
        self.faultString = message
        self.rpcid = rpcid
        if not message:
            import traceback
            self.faultString = traceback.format_exc()

    def error(self):
        return {"code": self.faultCode, "message": self.faultString}
    
    def response(self):
        return json.dumps({"jsonrpc": "2.0", "error":self.error(), "id":self.rpcid})

    def __repr__(self):
        return '<Fault %s: %s>' % (self.faultCode, self.faultString)

 
class TransportMixIn(object):
    '''XMLRPC Transport extended API
    '''
    user_agent = "jsonrpclib/0.1"
    _connection = (None, None)
    _extra_headers = []
        
    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "application/json-rpc")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)
            
    def getparser(self):
        target = JSONTarget()
        return JSONParser(target), target    
    

class JSONParser(object):
    
    def __init__(self, target):
        self.target = target

    def feed(self, data):
        self.target.feed(data)

    def close(self):
        pass


class JSONTarget(object):
    
    def __init__(self):
        self.data = []

    def feed(self, data):
        self.data.append(data)

    def close(self):
        return ''.join(self.data)


class Transport(TransportMixIn, xmlrpclib.Transport):
    
    def __init__(self, use_datetime):
        TransportMixIn.__init__(self)
        xmlrpclib.Transport.__init__(self, use_datetime)


class SafeTransport(TransportMixIn, xmlrpclib.SafeTransport):
    
    def __init__(self, use_datetime, context):
        TransportMixIn.__init__(self)    
        xmlrpclib.SafeTransport.__init__(self, use_datetime, context)


class SimpleJSONRPCRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    '''JSON-RPC请求处理器
    '''
    def is_rpc_path_valid(self):
        return True
    
    def do_POST(self):
        '''处理HTTP的POST请求
        '''
        if not self.is_rpc_path_valid():
            self.report_404()
            return
        try:
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)
            response = self.server._marshaled_dispatch(
                    data, getattr(self, '_dispatch', None), self.path
                )
            self.send_response(200)
        except Exception:
            response = Fault().response()
            self.send_response(500, response)
        if response is None:
            response = ''
        self.send_header("Content-type", "application/json-rpc")
        if self.encode_threshold is not None:
            if len(response) > self.encode_threshold:
                    q = self.accept_encodings().get("gzip", 0)
                    if q:
                        try:
                            response = xmlrpclib.gzip_encode(response)
                            self.send_header("Content-Encoding", "gzip")
                        except NotImplementedError:
                            pass
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
