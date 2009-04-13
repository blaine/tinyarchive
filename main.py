#!/usr/bin/env python

import cgi
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache

import models
import wsgiref.handlers

class MainHandler(webapp.RequestHandler):

  def get(self):
    template_file = os.path.join(os.path.dirname(__file__), 'templates/index.html')    
    self.response.out.write(template.render(template_file, {}))

class ArchiveHandler(webapp.RequestHandler):

  def get(self):
    results = models.ShortenedURL.gql("LIMIT 100")
    template_file = os.path.join(os.path.dirname(__file__), 'templates/archive.html')
    self.response.out.write(template.render(template_file, {'results': results}))

class UrlHandler(webapp.RequestHandler):

  def get(self):
    url = self.request.get('url')
    urls = models.get_by_url(url)

    template_file = os.path.join(os.path.dirname(__file__), 'templates/list.html')
    self.response.out.write(template.render(template_file, urls))

  def post(self):
    used_rev_canonical = False

    url = self.request.get('url')

    """ Only attempt to fetch the URL once per week. This isn't strict, since
        the storage is in memcache, but should prevent overly zealous attempts to
        cache URLs. """

    fetch_record = memcache.get(url)

    if fetch_record == 1:
      template_file = os.path.join(os.path.dirname(__file__), 'templates/recently_cached.html')
      self.response.out.write(template.render(template_file, {'url': url}))
      return
    else:
      memcache.set(url, 1, 604800)

    result = urlfetch.fetch(url=url, method=urlfetch.HEAD, follow_redirects=False)

    """ Okay, we found a redirect. Store it! """
    if result.status_code == 301 or result.status_code == 302:
      stored_url_ref = models.add_shortened_url(url, result.headers['location'])
      stored_url = models.ShortenedURL.get_by_id(stored_url_ref)
      template_file = os.path.join(os.path.dirname(__file__), 'templates/cached_success.html')
      self.response.out.write(template.render(template_file, {'stored_url': stored_url, 'url': url}))
      return

    """ No redirect. Let's try looking for the existence of rev=canonical. """
    revcanonical_url = "http://revcanonical.appspot.com/api?url=%s" % url
    revcanonical = urlfetch.fetch(url=revcanonical_url, method=urlfetch.GET, follow_redirects=False)
    if revcanonical.content:
      stored_url_ref = models.add_shortened_url(revcanonical.content, url)
      stored_url = models.ShortenedURL.get_by_id(stored_url_ref)
      template_file = os.path.join(os.path.dirname(__file__), 'templates/cached_success.html')
      self.response.out.write(template.render(template_file, {'stored_url': stored_url, 'url': url}))
      return

    """ All attempts to divine a short URL have failed. """
    template_file = os.path.join(os.path.dirname(__file__), 'templates/cached_failure.html')
    self.response.out.write(template.render(template_file, {'url': url}))

DEBUG = os.getenv('SERVER_SOFTWARE').split('/')[0] == "Development" if os.getenv('SERVER_SOFTWARE') else False

application = webapp.WSGIApplication(
    [
        ('/', MainHandler),
        ('/url', UrlHandler),
        ('/list', ArchiveHandler),
    ], debug=DEBUG)

def main():
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
