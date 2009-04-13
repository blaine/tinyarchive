from google.appengine.ext import db

class ShortenedURL(db.Model):
  short_version = db.StringProperty()
  canonical = db.StringProperty()
  date = db.DateTimeProperty(auto_now_add=True)

def add_shortened_url(short, canonical):
  try:
    surl = ShortenedURL(
             short_version=short,
             canonical=canonical
           )
    surl.put()
    return surl.key().id()
  except db.Error:
    return None

def get_by_url(url):
  short_matches = ShortenedURL.gql("WHERE short_version = :1", url)
  long_matches = ShortenedURL.gql("WHERE canonical = :1", url)
  return {'short_matches': short_matches, 'long_matches': long_matches, 'url': url}
