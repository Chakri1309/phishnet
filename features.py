"""
Feature extraction for phishing detection.
Maps any URL -> 30 UCI-style features in {-1, 0, 1}.

Feature order (must match training):
having_IP_Address, URL_Length, Shortining_Service, having_At_Symbol,
double_slash_redirecting, Prefix_Suffix, having_Sub_Domain, SSLfinal_State,
Domain_registeration_length, Favicon, port, HTTPS_token, Request_URL,
URL_of_Anchor, Links_in_tags, SFH, Submitting_to_email, Abnormal_URL,
Redirect, on_mouseover, RightClick, popUpWidnow, Iframe, age_of_domain,
DNSRecord, web_traffic, Page_Rank, Google_Index, Links_pointing_to_page,
Statistical_report
"""
import re
import socket
from urllib.parse import urlparse

FEATURE_NAMES = [
    'having_IP_Address', 'URL_Length', 'Shortining_Service', 'having_At_Symbol',
    'double_slash_redirecting', 'Prefix_Suffix', 'having_Sub_Domain', 'SSLfinal_State',
    'Domain_registeration_length', 'Favicon', 'port', 'HTTPS_token', 'Request_URL',
    'URL_of_Anchor', 'Links_in_tags', 'SFH', 'Submitting_to_email', 'Abnormal_URL',
    'Redirect', 'on_mouseover', 'RightClick', 'popUpWidnow', 'Iframe', 'age_of_domain',
    'DNSRecord', 'web_traffic', 'Page_Rank', 'Google_Index', 'Links_pointing_to_page',
    'Statistical_report',
]

EXPLANATIONS = {
    'having_IP_Address': 'Using an IP address instead of a domain name is a classic phishing trick.',
    'URL_Length': 'Very long URLs (>75 chars) hide the real destination. <54 is normal.',
    'Shortining_Service': 'URL shorteners (bit.ly, tinyurl…) hide the true domain.',
    'having_At_Symbol': '"@" in a URL makes the browser ignore everything before it — abused by phishers.',
    'double_slash_redirecting': '"//" appearing after position 7 means a sneaky redirect.',
    'Prefix_Suffix': 'A dash "-" in the domain (e.g. paypal-secure.com) mimics real brands.',
    'having_Sub_Domain': 'Too many dots / subdomains (e.g. login.paypal.evil.com) signals spoofing.',
    'SSLfinal_State': 'No HTTPS = traffic can be intercepted. Phishers often skip valid certs.',
    'Domain_registeration_length': 'Phishing domains are usually registered for <1 year (throwaway).',
    'Favicon': 'Fake sites often load the favicon from a foreign domain.',
    'port': 'Non-standard ports (other than 80/443) are suspicious.',
    'HTTPS_token': 'The word "https" inside the domain (e.g. https-secure.com) is a spoof trick.',
    'Request_URL': 'If images/scripts load from foreign domains, the page may be stitched together.',
    'URL_of_Anchor': 'Too many links pointing to foreign / empty anchors is suspicious.',
    'Links_in_tags': 'Meta/script/link tags pointing outside the site suggest cloning.',
    'SFH': 'A blank or foreign form handler means your password goes to criminals.',
    'Submitting_to_email': 'Forms that "mailto:" your data are stealing it.',
    'Abnormal_URL': 'URL doesn\'t match the claimed identity / WHOIS record.',
    'Redirect': 'Multiple redirects (>>1) are used to dodge blocklists.',
    'on_mouseover': 'Scripts that change the status bar hide the real link destination.',
    'RightClick': 'Disabling right-click tries to stop you inspecting the fraud.',
    'popUpWidnow': 'Popups asking for credentials are a phishing hallmark.',
    'Iframe': 'Hidden iframes load invisible malicious pages.',
    'age_of_domain': 'Legit domains are usually >6 months old; fresh ones are risky.',
    'DNSRecord': 'No DNS record / unresolvable host = highly suspicious.',
    'web_traffic': 'Very low-traffic (unpopular) domains are riskier for credential pages.',
    'Page_Rank': 'Low PageRank + asks for login = suspicious.',
    'Google_Index': 'Real sites are indexed by Google; brand-new phish pages often aren\'t.',
    'Links_pointing_to_page': 'Zero backlinks to a "bank login" page is a red flag.',
    'Statistical_report': 'URL/host appears in known phishing blacklists or uses phishy patterns.',
}

SHORTENERS = (
    'bit.ly|goo.gl|shorte.st|go2l.ink|x.co|ow.ly|t.co|tinyurl|tr.im|is.gd|cli.gs|'
    'yfrog.com|migre.me|ff.im|tiny.cc|url4.eu|twit.ac|su.pr|twurl.nl|snipurl.com|'
    'short.to|budurl.com|ping.fm|post.ly|just.as|bkite.com|snipr.com|fic.kr|loopt.us|'
    'doiop.com|short.ie|kl.am|wp.me|rubyurl.com|om.ly|to.ly|bit.do|lnkd.in|db.tt|'
    'qr.ae|adf.ly|cur.lv|tiny.cc|bitly.com|cutt.ly|rebrand.ly'
)

IP_RE = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$|^0x[0-9a-fA-F]+|\[?[0-9a-fA-F:]+\]?$')


def _ensure_scheme(url: str) -> str:
    url = (url or '').strip()
    if not url:
        return ''
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
        return 'http://' + url
    return url


def _lexical_features(url: str, parsed, host: str):
    f = {}
    f['having_IP_Address'] = -1 if IP_RE.match(host.split(':')[0]) else 1
    L = len(url)
    f['URL_Length'] = 1 if L < 54 else (0 if L <= 75 else -1)
    f['Shortining_Service'] = -1 if re.search(SHORTENERS, url, re.I) else 1
    f['having_At_Symbol'] = -1 if '@' in url else 1
    f['double_slash_redirecting'] = -1 if url.rfind('//') > 7 else 1
    f['Prefix_Suffix'] = -1 if '-' in host else 1
    dots = host.count('.')
    f['having_Sub_Domain'] = 1 if dots <= 1 else (0 if dots == 2 else -1)
    f['SSLfinal_State'] = 1 if parsed.scheme == 'https' else -1
    f['HTTPS_token'] = -1 if 'https' in host.lower() else 1
    # port
    try:
        port = parsed.port
        f['port'] = 1 if port in (None, 80, 443) else -1
    except ValueError:
        f['port'] = -1
    # redirect count heuristic: count of '//' , '>>' patterns + % encoding tricks
    redirect_markers = url.count('//') - 1 + url.lower().count('%2f') // 2
    f['Redirect'] = 1 if redirect_markers <= 0 else (0 if redirect_markers == 1 else -1)
    f['Abnormal_URL'] = f['having_IP_Address']  # refined later if WHOIS available
    return f


def _dns_feature(host: str):
    try:
        socket.setdefaulttimeout(3)
        socket.gethostbyname(host.split(':')[0])
        return 1
    except Exception:
        return -1


def _whois_features(host: str):
    """Try python-whois; fall back to neutral 0."""
    try:
        import whois
        from datetime import datetime, timezone
        w = whois.whois(host)
        creation = w.creation_date
        expiration = w.expiration_date
        if isinstance(creation, list):
            creation = creation[0]
        if isinstance(expiration, list):
            expiration = expiration[0]
        now = datetime.now(timezone.utc)
        age_days, reg_days = None, None
        if creation:
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            age_days = (now - creation).days
        if creation and expiration:
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=timezone.utc)
            reg_days = (expiration - creation).days
        age = 1 if (age_days is not None and age_days > 180) else (-1 if age_days is not None else 0)
        reg = 1 if (reg_days is not None and reg_days > 365) else (-1 if reg_days is not None else 0)
        abnormal = 1 if age == 1 else 0
        return age, reg, abnormal
    except Exception:
        return 0, 0, 0


def _content_features(url: str, parsed, host: str):
    """Fetch page (short timeout) and compute content-based features.
    Falls back to neutral/safe defaults when offline."""
    defaults = dict(Favicon=1, Request_URL=1, URL_of_Anchor=0, Links_in_tags=0,
                    SFH=0, Submitting_to_email=1, on_mouseover=1, RightClick=1,
                    popUpWidnow=1, Iframe=1)
    try:
        import requests
        from bs4 import BeautifulSoup
        r = requests.get(url, timeout=4, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
        if r.status_code >= 400 or not r.text:
            return defaults
        soup = BeautifulSoup(r.text[:300000], 'html.parser')
        text = r.text.lower()

        # Favicon
        try:
            icon = soup.find('link', rel=re.compile('icon', re.I))
            if icon and icon.get('href'):
                href = icon['href']
                defaults['Favicon'] = 1 if (host in href or href.startswith('/') or href.startswith('.')) else -1
        except Exception:
            pass
        # Request_URL: % of external objects
        try:
            tags = [('img', 'src'), ('script', 'src'), ('link', 'href'), ('video', 'src'), ('audio', 'src')]
            total, ext = 0, 0
            for tag, attr in tags:
                for el in soup.find_all(tag):
                    src = el.get(attr)
                    if src:
                        total += 1
                        if src.startswith('http') and host not in src:
                            ext += 1
            if total:
                pct = ext / total * 100
                defaults['Request_URL'] = 1 if pct < 22 else (0 if pct < 61 else -1)
        except Exception:
            pass
        # URL_of_Anchor
        try:
            anchors = soup.find_all('a', href=True)
            if anchors:
                bad = sum(1 for a in anchors if a['href'].strip().lower() in ('#', '#skip', 'javascript:void(0)')
                          or (a['href'].startswith('http') and host not in a['href']))
                pct = bad / len(anchors) * 100
                defaults['URL_of_Anchor'] = 1 if pct < 31 else (0 if pct < 67 else -1)
        except Exception:
            pass
        # Links_in_tags
        try:
            metas = soup.find_all(['meta', 'script', 'link'])
            if metas:
                ext = sum(1 for m in metas for attr in ('src', 'href', 'content')
                          if m.get(attr) and str(m.get(attr)).startswith('http') and host not in str(m.get(attr)))
                pct = ext / max(len(metas), 1) * 100
                defaults['Links_in_tags'] = 1 if pct < 17 else (0 if pct < 81 else -1)
        except Exception:
            pass
        # SFH
        try:
            forms = soup.find_all('form')
            if forms:
                worst = 1
                for form in forms:
                    action = (form.get('action') or '').strip()
                    if action in ('', 'about:blank'):
                        worst = min(worst, 0)
                    elif action.startswith('http') and host not in action:
                        worst = -1
                defaults['SFH'] = worst
        except Exception:
            pass
        defaults['Submitting_to_email'] = -1 if ('mailto:' in text or 'mail(' in text) else 1
        defaults['on_mouseover'] = -1 if 'onmouseover' in text else 1
        defaults['RightClick'] = -1 if ('event.button==2' in text.replace(' ', '') or 'contextmenu' in text and 'preventdefault' in text) else 1
        defaults['popUpWidnow'] = -1 if 'window.open' in text and 'prompt' in text else (0 if 'window.open' in text else 1)
        defaults['Iframe'] = -1 if '<iframe' in text and ('hidden' in text or 'display:none' in text or 'width="0"' in text) else (0 if '<iframe' in text else 1)
        return defaults
    except Exception:
        return defaults


def extract_features(url: str) -> dict:
    """Main entry: URL string -> {feature_name: -1/0/1}."""
    raw = _ensure_scheme(url)
    parsed = urlparse(raw)
    host = (parsed.netloc or parsed.path.split('/')[0]).lower().strip()
    if not host:
        # totally invalid -> all phishing-leaning
        return {name: -1 for name in FEATURE_NAMES}
    lex = _lexical_features(raw, parsed, host)
    dns = _dns_feature(host)
    age, reg_len, abnormal = _whois_features(host)
    content = _content_features(raw, parsed, host)

    feats = {}
    feats['having_IP_Address'] = lex['having_IP_Address']
    feats['URL_Length'] = lex['URL_Length']
    feats['Shortining_Service'] = lex['Shortining_Service']
    feats['having_At_Symbol'] = lex['having_At_Symbol']
    feats['double_slash_redirecting'] = lex['double_slash_redirecting']
    feats['Prefix_Suffix'] = lex['Prefix_Suffix']
    feats['having_Sub_Domain'] = lex['having_Sub_Domain']
    feats['SSLfinal_State'] = lex['SSLfinal_State']
    feats['Domain_registeration_length'] = reg_len
    feats['Favicon'] = content['Favicon']
    feats['port'] = lex['port']
    feats['HTTPS_token'] = lex['HTTPS_token']
    feats['Request_URL'] = content['Request_URL']
    feats['URL_of_Anchor'] = content['URL_of_Anchor']
    feats['Links_in_tags'] = content['Links_in_tags']
    feats['SFH'] = content['SFH']
    feats['Submitting_to_email'] = content['Submitting_to_email']
    feats['Abnormal_URL'] = abnormal if abnormal != 0 else lex['Abnormal_URL']
    feats['Redirect'] = lex['Redirect']
    feats['on_mouseover'] = content['on_mouseover']
    feats['RightClick'] = content['RightClick']
    feats['popUpWidnow'] = content['popUpWidnow']
    feats['Iframe'] = content['Iframe']
    feats['age_of_domain'] = age
    feats['DNSRecord'] = dns
    # traffic / rank heuristics without paid APIs
    feats['web_traffic'] = 0
    feats['Page_Rank'] = 0
    feats['Google_Index'] = 1 if dns == 1 else -1
    feats['Links_pointing_to_page'] = 0
    # blacklist heuristic
    suspicious_count = sum(1 for k in ('having_IP_Address', 'Shortining_Service', 'having_At_Symbol',
                                       'Prefix_Suffix', 'HTTPS_token') if lex.get(k) == -1)
    feats['Statistical_report'] = -1 if (suspicious_count >= 2 or lex['having_IP_Address'] == -1) else 1
    return feats


def features_to_vector(feats: dict):
    return [int(feats.get(n, 0)) for n in FEATURE_NAMES]


if __name__ == '__main__':
    import sys, json
    u = sys.argv[1] if len(sys.argv) > 1 else 'http://google.com'
    print(json.dumps(extract_features(u), indent=2))
