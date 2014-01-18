BASE_URL = 'http://www.nbc.com'
CURRENT_SHOWS = '%s/shows/' % BASE_URL
CLASSIC_TV = '%s/classic-tv/' % BASE_URL

# Thumbs
# %d = 360, or 480 for classic tv
# %s = 'nbc2', or 'nbcrewind2' for classic tv
# %s = pid
THUMB_URL = 'http://video.nbc.com/player/mezzanine/image.php?w=640&h=%d&path=%s/%s_mezzn.jpg&trusted=yes'

RE_BASE_URL = Regex('(http://[^/]+)')
RE_THUMB_SIZE = Regex('w=[0-9]+&h=[0-9]+')
RE_SHOW_ID = Regex('nbc.com/([^/]+)/')

####################################################################################################
def Start():

	ObjectContainer.title1 = 'NBC'
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:26.0) Gecko/20100101 Firefox/26.0'

####################################################################################################
@handler('/video/nbc', 'NBC')
def MainMenu():

	oc = ObjectContainer()

	if not Client.Platform in ('Android', 'iOS', 'Roku', 'Safari', 'Firefox', 'Chrome', 'Windows', 'Windows Phone'):
		oc.header = 'Not supported'
		oc.message = 'This channel is not supported on %s' % (Client.Platform if Client.Platform is not None else 'this client')
		return oc

	oc.add(DirectoryObject(key=Callback(CurrentShows), title='Current Shows'))
	oc.add(DirectoryObject(key=Callback(ClassicTV), title='Classic TV'))

	return oc

####################################################################################################
@route('/video/nbc/currentshows')
def CurrentShows():

	oc = ObjectContainer(title2='Current Shows')
	show_ids = []
	content = HTML.ElementFromURL(CURRENT_SHOWS)

	for show in content.xpath('//a[@title="Full Episodes"]/parent::td/preceding-sibling::td[6]'):
		url = show.xpath('./a/@href')[0]
		if '/classic-tv/' in url:
			continue
		url = '%s/video/' % url.rstrip('/')

		title = show.xpath('./a/p/text()')[0].strip()

		oc.add(DirectoryObject(
			key = Callback(Show, show=title, url=url),
			title = title
		))

	# Ugh, NBC site is *still* a big mess, even after the 5667654563465787 updates they did...
	# Add those 2 nice shows manually, other missing shows are mostly crap and not worth watching anyway.
	oc.add(DirectoryObject(
		key = Callback(Show, show='Community', url='http://www.nbc.com/community/video/'),
		title = 'Community'
	))

	oc.add(DirectoryObject(
		key = Callback(Show, show='Hannibal', url='http://www.nbc.com/hannibal/video/'),
		title = 'Hannibal'
	))

	oc.objects.sort(key=lambda obj: obj.title.replace('The ', ''))
	return oc

####################################################################################################
@route('/video/nbc/classictv')
def ClassicTV():

	oc = ObjectContainer(title2='Classic TV')
	content = HTML.ElementFromURL(CLASSIC_TV)

	for show in content.xpath('//h2[text()="classic tv"]/following-sibling::div//div[@class="thumb-block"]'):
		url = show.xpath('.//a[contains(@href, "/classic-tv/") and contains(@href, "/video")]/@href')
		if len(url) < 1:
			continue

		url = url[0]
		title = show.xpath('.//div[@class="title"]/text()')[0].strip()
		thumb = show.xpath('.//img/@src')[0]
		thumb = thumb.replace('150x84xC', '640x360xC')

		oc.add(DirectoryObject(
			key = Callback(Show, show=title, url=url, thumb=thumb),
			title = title,
			thumb = Resource.ContentsOfURLWithFallback(thumb)
		))

	return oc

####################################################################################################
@route('/video/nbc/show')
def Show(show, url):

	oc = ObjectContainer(title2=show)

	try: base = RE_BASE_URL.search(url).group(1)
	except: base = BASE_URL

	if url.find('http://') == -1:
		url = base + url

	content = HTML.ElementFromURL(url)

	for category in content.xpath('//*[text()="Full Episodes" or text()="FULL EPISODES"]/following-sibling::ul[1]/li/a[contains(@href, "categories")]'):
		title = category.text.strip()
		url = category.get('href')

		if url.find('http://') == -1:
			url = base + url

		oc.add(DirectoryObject(
			key = Callback(Episodes, show=show, title=title, url=url, base=base),
			title = title
		))

	if len(oc) == 0:
		return ObjectContainer(header='Empty', message='This directory is empty')

	return oc

####################################################################################################
@route('/video/nbc/episodes')
def Episodes(show, title, url, base):

	oc = ObjectContainer(title1=show, title2=title)
	content = HTML.ElementFromURL(url)

	for episode in content.xpath('//div[contains(@class, "thumb-view")]//div[contains(@class, "thumb-block")]'):
		video_url = episode.xpath('./a/@href')[0]

		if video_url.find('http://') == -1:
			video_url = base + video_url

		episode_title = episode.xpath('.//div[@class="title"]')[0].text.strip()
		air_date = episode.xpath('./div[@class="meta"]/p')[0].text.split(': ', 1)[1]
		date = Datetime.ParseDate(air_date).date()
		thumb = episode.xpath('.//img/@src')[0]
		thumb = RE_THUMB_SIZE.sub('w=640&h=360', thumb)

		oc.add(EpisodeObject(
			url = video_url,
			show = show,
			title = episode_title,
			originally_available_at = date,
			thumb = Resource.ContentsOfURLWithFallback(thumb)
		))

	# More than 1 page?
	if len(content.xpath('//div[@class="nbcu_pager"]')) > 0:
		next_url = base + content.xpath('//div[@class="nbcu_pager"]//a[text()="Next"]/@href')[0]

		if next_url != url:
			oc.add(NextPageObject(key=Callback(Episodes, title=title, url=next_url, base=base), title='Next ...'))

	if len(oc) < 1:
		return ObjectContainer(header='Empty', mesage='This directory is empty')

	return oc
