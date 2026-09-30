import sys
sys.path.append("/home/logan78/Desktop/airfare-index-bot")

from packages.scraping.core.fetchers.base import Request, Response
from packages.scraping.core.session.session_manager import SessionManager
from packages.scraping.core.proxy.proxy_manager import ProxyManager

def test_session_manager():
    sm = SessionManager()
    
    # Test cookie parsing with commas in dates
    req = Request(url="https://example.com")
    headers = {
        "Set-Cookie": "session_id=12345; Expires=Wed, 21 Oct 2015 07:28:00 GMT; Path=/, another_cookie=67,890; Path=/, data=a,b,c; Path=/"
    }
    resp = Response(request=req, status=200, headers=headers, body=b"")
    sm.update_from_response(resp)
    
    print("Parsed cookies:", sm.cookies)
    
def test_proxy_manager():
    pm = ProxyManager(proxies=["http://proxy1", "http://proxy2"])
    
    pm.report_status("http://proxy1", 200, "<html><body><div class=\"g-recaptcha\"></div></body></html>")
    
    print("Quarantined:", pm.quarantined)

if __name__ == "__main__":
    test_session_manager()
    test_proxy_manager()
