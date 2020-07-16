import requests
from bs4 import BeautifulSoup
import json
import re
import os
from lxml import etree

from urllib import request


def createUrl(commentUrl, offset, limit):
    s1 = 'http://comment.api.163.com/api/v1/products/a2869674571f77b5a0867c3d71db5856/threads/'
    s2 = '/comments/newList?offset='
    name = commentUrl.split('/')[-1].split('.')[0]
    u = s1 + str(name) + s2 + str(offset) + '&limit=' + str(limit)
    return u


def get_news_url(typeUrl, typeName, typePages):
    # 爬取网易新闻的目录
    # 文件名为 newsurls_新闻类型.json
    # json文件内容为：新闻类型、新闻标题、新闻链接
    urls = []
    url_first = 'http://gov.163.com/special/' + typeUrl + '/'
    urls.append(url_first)
    pagenum = typePages
    for i in range(2, pagenum + 1):
        urls.append('http://gov.163.com/special/{}_{:0>2d}/'.format(typeUrl, i))

    # print(urls)
    urls_file = './newsurls/newsurls_' + typeUrl + '.json'
    with open(urls_file, 'w', encoding='utf-8') as fp:
        
        for url in urls:
            print(url)
            wbdata = requests.get(url).text
            soup = BeautifulSoup(wbdata, 'lxml')
            # soup = BeautifulSoup(wbdata,'html.parser')
            news_titles = soup.select('div .subPage-colLM ul>li>a')

            for n in news_titles:
                title = n.get_text()
                link = n.get('href')
                news_titles_url = {
                    'type': typeName,
                    'title': title,
                    'link': link
                }
                # 每个新闻标题占一行，以便json.load()读取
                json.dump(news_titles_url, fp, ensure_ascii=False)
                fp.write('\n')


def get_newstypes():
    # 读取新闻类型
    # 当前已知网易政务新闻的栏目
    # { "typeUrl": "central", "typeName": "中央政务", "typePages": 15},
    # { "typeUrl": "locality", "typeName": "地方政务", "typePages": 10},
    # { "typeUrl": "yangqi", "typeName": "央企", "typePages": 15},
    # { "typeUrl": "zwzx_n", "typeName": "政务要闻", "typePages": 15},
    # { "typeUrl": "dffg_n", "typeName": "政策解读", "typePages": 15},
    # { "typeUrl": "gcdt_n", "typeName": "学习之声", "typePages": 15},
    # { "typeUrl": "voice", "typeName": "凡人微光", "typePages": 15},
    # { "typeUrl": "dfdj", "typeName": "党风党建", "typePages": 1},
    # { "typeUrl": "jjjs_n", "typeName": "经济发展", "typePages": 15},
    # { "typeUrl": "cityandfestival_n", "typeName": "文化中国", "typePages": 15}
    with open("./newsurls/newstype.json", 'r') as load_f:
        newstypes = json.load(load_f)
    return newstypes


def get_newslist():
    newstypes = get_newstypes()
    for newstype in newstypes:
        # 根据新闻的类型/栏目分别读取
        typeUrl = newstype['typeUrl']
        typeName = newstype['typeName']
        typePages = newstype['typePages']
        # print(typeUrl, typeName,typePages)
        get_news_url(typeUrl, typeName, typePages)


def get_content(url):
    # 爬取网易新闻的正文
    date_time = ''  # 新闻的日期和时间是一个整体字串
    newsdate = ''   # 拆分出新闻日期
    newstime = ''   # 拆分出新闻时间
    source = ''     # 新闻来源
    author = ''     # 新闻作者
    body = ''       # 新闻内容

    try:
        resp = requests.get(url, stream=True)
        if resp.status_code == 200:
            html = resp.text
            bs4 = BeautifulSoup(html, 'lxml')
            # print('bs4 : ',bs4)
            # 先整体读取新闻的日期和时间字串，再用正则分别提取 日期 newsdate 时间 newstime
            date_time = bs4.find('div', class_='post_time_source').get_text()    
            newsdate =  re.search(r"(\d{4}-\d{1,2}-\d{1,2})", date_time).group(0)
            newstime =  re.search(r"(\d{1,2}:\d{1,2}:\d{1,2})", date_time).group(0)
            source = bs4.find('a', id='ne_article_source').get_text()
            author = bs4.find('span', class_='ep-editor').get_text()
            body = bs4.find('div', class_='post_text').get_text()
        else:
            print('This page has NO news {} : {}'.format(resp.status_code, url))
    except:
        # 如果页面解析出现任何问题，文章内容置空，表示此页新闻无效
        body = ''

    # print('newsdate, newstime, source, author',newsdate, newstime, source, author)

    # 如果新闻返回内容为空 body = '' 则判断此篇新闻无效
    return newsdate, newstime, source, author, body

def get_news_comments(newsID, comments):
    # 爬取某一个新闻的评论页的所有评论
    # newsID : 新闻url的网址编号，如：8EQFGO0300234IG9 (.html)
    # comments : 此篇新闻的总评论数

    commentUrl = 'http://comment.tie.163.com/' + newsID +'.html'
    # commentUrl = 'http://comment.tie.163.com/A1MHRIAH00234KIR.html'

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36'}

    # step  : 每页的评论数，爬取的步长
    step = 30
    news_comments = []
    for i in range(0, comments, step):
        res = requests.get(url=createUrl(commentUrl, offset=i, limit=step), headers=headers).content
        try:
            data = json.loads(res.decode())
        except:
            # 评论页因为网络等原因，返回的不是json格式，会报错
            # 如果出现错误，则放弃本页评论，提取下一页评论
            continue
        for key in data['comments'].keys():
            # print(data['comments'][key]['content'])
            news_comments.append(data['comments'][key]['content'])

    return news_comments

def save_comments(newstype):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36'}
    filename = './newsurls/newsurls_{}.json'.format(newstype)
    with open(filename, 'r') as f:
        filenum = 0
        for line in f.readlines():
            json_data = json.loads(line)
            news_link = json_data['link']
            filenum += 1
            newsID = news_link.split('/')[-1].split('.')[-2]
            # 根据newstype建立分类目录
            # 先判断路径是否存在
            path = './comments/{}'.format(newstype)
            isExists = os.path.exists(path)
            # 如果不存在则创建目录
            if not isExists:
                print('Creating folder : {}'.format(path))
                os.makedirs(path)

            comments_filename = '{}/{:0>6d}_{}.json'.format(path, filenum, newsID)
            print('Writing in ',comments_filename)
            with open(comments_filename, 'w',encoding='utf-8') as fc:  # file of comments
                # 从文章中获取
                # newsdate newstime : 新闻的日期、时间
                # source : 文章来源
                # author : 文章作者
                # body   : 文章内容
                newsdate, newstime, source, author, body = get_content(news_link)
                
                # 如果新闻的内容返回为空，则可能此条新闻已经失效
                if body == '':
                    print('This news page reading FAIL : ',news_link)
                    with open('newsfail.csv', 'a') as ferror:
                        ferror.write('{},{}\n'.format(filenum,news_link))
                    continue

                # 用bs4不能获取动态网页的评论数，所以用requests再取一遍网页
                # 通过json['newListSize']获取评论页的跟帖数
                commentUrl = 'http://comment.tie.163.com/{}.html'.format(newsID)
                res = requests.get(url=createUrl(commentUrl, offset=0, limit = 30), headers=headers).content
                try:
                    comments = json.loads(res.decode())['newListSize']
                except:
                    comments = 0

                # 获取新闻对应的评论内容
                news_comments = get_news_comments(newsID, comments)

                news_content = {
                    'ID' : newsID,
                    'type' : json_data['type'],
                    'comments' : len(news_comments),
                    'title' : json_data['title'],
                    'newsdate' : newsdate,
                    'newstime' : newstime,
                    'source': source,
                    'author': author,
                    'body': body
                }

                # 把新闻的内容和评论重新组合为字典
                news_content_comments = {'news_content': news_content, 'news_comments': news_comments} 
                # 写入json文件
                json.dump(news_content_comments, fc, ensure_ascii=False)
                # fc.write('\n')

# 通过预设的新闻类型（栏目）获取各栏目的新闻文章列表
# 并栏目写入json文件中，以备后面分栏目调用
get_newslist()

# 获取新闻栏目列表，分栏目获取每条新闻的内容详情和评论
# newstypes = json.loads(get_newstypes())
newstypes = get_newstypes()

for newstype in newstypes:
    # 遍历每类新闻
    # 用 json.dumps 的方法格式化json数据
    # 如果不先 dumps 总会报错
    s1 = json.dumps(newstype)
    newstypeUrl = json.loads(s1)['typeUrl']
    newstypeName = json.loads(s1)['typeName']
    print('Processing 【{}】 in URL : ./{}'.format(newstypeName, newstypeUrl))
    save_comments(newstypeUrl)

# get_news_comments('A1MHRIAH00234KIR')

# 中央政务
# save_comments('central')
# 政务要闻
# save_comments('zwzx_n')
# 凡人微光
# save_comments('voice')
