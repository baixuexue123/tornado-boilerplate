import re
from math import floor, ceil
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from utils.text import force_text, force_bytes


def url_replace_param(url, name, value):
    """
    Replace a GET parameter in an URL
    """
    url_components = urlparse(force_bytes(url))
    query_params = parse_qs(force_text(url_components.query))
    query_params[name] = value
    query = urlencode(query_params, doseq=True)
    return force_text(urlunparse([
        url_components.scheme,
        url_components.netloc,
        url_components.path,
        url_components.params,
        force_bytes(query),
        url_components.fragment,
    ]))


def get_pagination_context(current_page, total, page_size, pages_to_show=11,
                           url=None, extra=None, parameter_name='page'):
    """
    Generate pagination context
    current_page: 当前页码
    total: 数据总行数
    page_size: 每页显示的条数
    pages_to_show: 分页器上显示多少个页码
    parameter_name: 页码参数名
    """
    if total <= 0:
        num_pages = 1  # 共有多少页
    else:
        num_pages = ceil(total / page_size)

    half_page_num = floor(pages_to_show / 2)  # 中间位置的页码
    if half_page_num < 0:
        half_page_num = 0

    first_page = current_page - half_page_num
    if first_page <= 1:
        first_page = 1
    if first_page > 1:
        pages_back = first_page - half_page_num
        if pages_back < 1:
            pages_back = 1
    else:
        pages_back = None

    last_page = first_page + pages_to_show - 1
    if pages_back is None:
        last_page += 1
    if last_page > num_pages:
        last_page = num_pages
    if last_page < num_pages:
        pages_forward = last_page + half_page_num
        if pages_forward > num_pages:
            pages_forward = num_pages
    else:
        pages_forward = None
        if first_page > 1:
            first_page -= 1
        if pages_back is not None and pages_back > 1:
            pages_back -= 1
        else:
            pages_back = None

    pages_shown = []
    for i in range(first_page, last_page + 1):
        pages_shown.append(i)
        # Append proper character to url

    if url:
        # Remove existing page GET parameters
        url = force_text(url)
        url = re.sub(r'\?{0}\=[^\&]+'.format(parameter_name), '?', url)
        url = re.sub(r'\&{0}\=[^\&]+'.format(parameter_name), '', url)
        # Append proper separator
        if '?' in url:
            url += '&'
        else:
            url += '?'
    # Append extra string to url
    if extra:
        if not url:
            url = '?'
        url += force_text(urlencode(extra)) + '&'
    if url:
        url = url.replace('?&', '?')

    context = {
        'pagination_url': url,
        'num_pages': num_pages,
        'page_size': page_size,
        'current_page': current_page,
        'first_page': first_page,
        'last_page': last_page,
        'pages_shown': pages_shown,
        'pages_back': pages_back,
        'pages_forward': pages_forward,
        'parameter_name': parameter_name,
        'url_replace_param': url_replace_param,
    }
    return context
