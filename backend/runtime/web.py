"""Bounded HTTPS document reader. Pins a public address for each connection.

No cookies, authentication, browser sessions, scripts or private-network requests.
"""
import http.client
import ipaddress
import socket
import ssl
import urllib.parse
from html.parser import HTMLParser
from .protocol import Fault

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0;self.title=False;self.titles=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'):self.skip+=1
        if tag=='title':self.title=True
        if tag in ('p','div','h1','h2','li','br'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'):self.skip=max(0,self.skip-1)
        if tag=='title':self.title=False
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
        if self.title:self.titles.append(data)

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,address):super().__init__(host,443,timeout=10,context=ssl.create_default_context());self.address=address
    def connect(self):
        sock=socket.create_connection((self.address,443),self.timeout)
        self.sock=self._context.wrap_socket(sock,server_hostname=self.host)

def read(url):
    for _ in range(4):
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):
            raise Fault('url_denied','只接受不含凭据的公网 HTTPS 地址')
        host=parsed.hostname.encode('idna').decode()
        # Existing mailbox ban remains in force; this is a public document reader.
        if host in {'mail.163.com','mail.vimalinx.com','imap.163.com','smtp.163.com'}:
            raise Fault('url_denied','不提供邮箱访问')
        addresses=list(dict.fromkeys(x[4][0] for x in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)))
        if not addresses or not all(ipaddress.ip_address(a).is_global for a in addresses):
            raise Fault('url_denied','不允许访问本机或私网地址')
        connection=PinnedHTTPS(host,addresses[0])
        try:
            connection.request('GET',urllib.parse.urlunsplit(('', '',parsed.path or '/',parsed.query,'')),headers={'User-Agent':'WanjieGate/0.1','Accept':'text/html,text/plain,application/json'})
            response=connection.getresponse()
            if response.status in (301,302,303,307,308):
                location=response.getheader('Location')
                if not location:raise Fault('invalid_response','跳转缺少目标')
                url=urllib.parse.urljoin(url,location);continue
            if response.status!=200:raise Fault('web_unavailable',f'网页返回 HTTP {response.status}')
            raw=response.read(1000001)
            if len(raw)>1000000:raise Fault('response_too_large','网页超过 1 MB')
            mime=response.getheader('Content-Type','')
            if not any(t in mime for t in ('text/html','text/plain','application/json')):raise Fault('unsupported_media','此能力只读取文本网页')
            content=raw.decode('utf-8',errors='replace')
            if 'html' in mime:
                parser=Text();parser.feed(content);text=''.join(parser.parts);title=''.join(parser.titles).strip()
            else:text=content;title=host
            return {'url':url,'title':title or host,'text':text[:50000]}
        finally:connection.close()
    raise Fault('too_many_redirects','网页跳转过多')
