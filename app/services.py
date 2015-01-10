# -*- coding: utf-8 -*-

from app import app, db, bbcode_parser
from models import User, Picture, Post, Forum, ForumTopic, ForumPost
from slugify import slugify
import pygeoip, os
from datetime import datetime


class PostService(object):
	@classmethod
	def insert(cls, post):
		post = PostService._upsert(post)
		db.session.add(post)
		db.session.commit()
		return post

	@classmethod
	def update(cls, post):
		post = PostService._upsert(post)
		db.session.add(post)
		db.session.commit()
		pass

	@classmethod
	def _upsert(cls, post):
		parts = post.body.split("[more]")
		post.preview_html = bbcode_parser.format(parts[0].strip())
		if len(parts) > 1:
			post.body_html = bbcode_parser.format(parts[1].strip())
		if post.slug is None:
			ttitle = post.title
			if ttitle.startswith('topic'):
				ttitle = 'blog-'+ttitle
			post.slug = safe_slugify(Post, post, ttitle)
		return post


class CommentService(object):
	@classmethod
	def insert(cls, forum):
		forum.slug = safe_slugify(Forum, forum, forum.title)
		db.session.add(forum)
		db.session.commit()



class ForumService(object):
	@classmethod
	def insert(cls, forum):
		forum.slug = safe_slugify(Forum, forum, forum.title)
		db.session.add(forum)
		db.session.commit()


class ForumTopicService(object):
	@classmethod
	def insert(cls, topic):
		topic.body_html = bbcode_parser.format(topic.body.strip())
		topic.slug = safe_slugify(ForumTopic, topic, 'topic-'+topic.title)
		db.session.add(topic)
		db.session.commit()
		forum = topic.forum
		forum.last_post_id = forum.id
		forum.total_topics = (forum.total_topics or 0) + 1
		db.session.add(forum)
		db.session.commit()
		return topic
	@classmethod
	def update(cls, topic):
		topic.body_html = bbcode_parser.format(topic.body.strip())
		if topic.slug is None:
			topic.slug = safe_slugify(ForumTopic, topic, 'topic-'+topic.title)
		db.session.add(topic)
		db.session.commit()
		return topic


class ForumPostService(object):
	@classmethod
	def insert(cls, post):
		post.body_html = bbcode_parser.format(post.body.strip())
		db.session.add(post)
		db.session.commit()
		topic = post.topic
		topic.last_post_id = post.id
		topic.total_posts = (topic.total_posts or 0) + 1
		db.session.add(topic)
		forum = post.forum
		forum.last_post_id = post.id
		db.session.add(forum)
		db.session.commit()
		return post
	@classmethod
	def update(cls, post):
		post.body_html = bbcode_parser.format(post.body.strip())
		db.session.add(post)
		db.session.commit()
		return post



# ---------- HELPERS ---------------
basedir = os.path.abspath(os.path.dirname(__file__))
rawdata = pygeoip.GeoIP(os.path.join(basedir, '../GeoLiteCity.dat'))
def ipquery(ip):
	data = rawdata.record_by_name(ip)
	return data

def safe_slugify(cls, obj, text):
	slug = slugify(text)
	slug_result = slug
	i = 1
	while True:
		obj = db.session.query(cls).filter(cls.slug==slug_result, cls.id != obj.id).first()
		if obj is None:
			return slug_result
		slug_result = slug+'_'+str(i)
		i += 1