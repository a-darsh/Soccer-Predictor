from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
from threading import Thread

HEADERS = {'User-Agent': UserAgent().chrome}
REDDIT_URL = 'https://old.reddit.com/'


def search_reddit(term, subreddit, max_post_count):
  query = term.replace(' ', '+')
  page = None
  if subreddit == None:
    page = requests.get(REDDIT_URL+'search', params='q='+query, headers=HEADERS)
  else:
    page = requests.get(REDDIT_URL+'r/'+subreddit+'/search', params='q='+query+'&restrict_sr=on', headers=HEADERS)
  links = post_links(BeautifulSoup(page.text, 'lxml'))

  threads = list()
  posts = list()
  for i, link in enumerate(links):
    thread = Thread(target=process_post, args=(link, posts))
    thread.start()
    threads.append(thread)

    if (i + 1) >= max_post_count:
      break

  for thread in threads:
    thread.join()

  return {
    'term': term,
    'subreddit': subreddit,
    'url': page.url,
    'posts': posts,
  }

def process_post(link, posts):
  print(f'Processing {link}')
  post_page = requests.get(link, params='limit=500', headers=HEADERS)
  posts.append(post_info(BeautifulSoup(post_page.text, 'lxml'), link))

def post_links(soup):
  links = list()
  post_section = soup.find('header', {'class': 'search-result-group-header'}).parent
  for link in post_section.findAll('a', {'class': 'search-title', 'href': True}):
    links.append(link['href'])

  return links


def post_info(soup, url):
  comments = list()
  for entry in soup.find('div', {'class': 'commentarea'}).findAll('div', {'class': 'entry'}):
    comment = parse_entry(entry, entry.find('p', {'class': 'tagline'}), True)
    if valid_comment(comment):
      comments.append(comment)

  return {
    'url': url,
    'title': parse_text(soup.find('a', {'class': 'title'})),
    'post': parse_entry(soup.find('div', {'class': 'expando'}), soup.find('div', {'class': 'sitetable'}), False),
    'comments': comments,
  }


def parse_entry(body_container, meta_container, is_comment):
  body = None
  if body_container != None:
    body = parse_text(body_container.find('div', {'class': 'usertext-body'}))

  date = meta_container.find('time', {'datetime': True})
  if date != None:
    date = date['datetime']

  score_element = 'span' if is_comment else 'div'

  return {
    'body': body,
    'score': parse_points(parse_text(meta_container.find(score_element, {'class': 'score unvoted'}))),
    'likes': parse_points(parse_text(meta_container.find(score_element, {'class': 'score likes'}))),
    'dislikes': parse_points(parse_text(meta_container.find(score_element, {'class': 'score dislikes'}))),
    'author': parse_text(meta_container.find('a', {'class': 'author'})),
    'date': date,
  }


def parse_text(value):
  if value == None:
    return None
  return value.text


def parse_points(value):
  if value == None:
    return None
  
  value = value.split(' ', 1)[0]
  if value[-1].lower() == 'k':
    return round(float(value[:-1]) * 1_000)
  elif value[-1].lower() == 'm':
    return round(float(value[:-1]) * 1_000_000)

  return int(value)


def valid_comment(comment):
  # filter out deleted, removed, and unloaded comments
  if ['[deleted]\n\n', '[removed]\n\n', None].__contains__(comment['body']):
    return False
  
  # filter out moderator comments
  if ['AutoModerator'].__contains__(comment['author']):
    return False
  
  return True