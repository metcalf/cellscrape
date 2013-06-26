Hacked together little scraping utility for processing a CSV of cell device penetration data.  Results of the analysis [here](http://www.throughawall.com/blog/2013/05/14/infographic-mobile-kenya/).

Cellscrape does a few things:

* Search GSM Arena for a phone spec page matching a name
* Scrape the appropriate GSM arena page
* Parse the scraped data into CSV

Analysis prints out some basic summary statistics on the scraped data.

Depends on PrettyTable, BeautifulSoup, simplejson and Python 2.7
