# Commercial airline passenger counts per year

These scripts collect the data for and build maps representing some of the most popular commercial airline routes around the world.

This [blog post](http://tech.marksblogg.com/popular-airline-passenger-routes.html) explains more.

# Installation

These instructions were tested on a fresh Ubuntu 14.04 installation.

```bash
$ sudo apt-get update
$ sudo apt-get install python-mpltoolkits.basemap pandoc libxml2-dev libxslt1-dev redis-server
$ sudo pip install docopt
```

```bash
$ virtualenv airline_passenger_counts
$ source airline_passenger_counts/bin/activate
$ pip install -r requirements.txt
```

# Usage

Download Wikipedia's ~11GB Bzip'ed XML dump of their English language articles:

```bash
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles1.xml-p000000010p000010000.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles2.xml-p000010002p000025001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles3.xml-p000025001p000055000.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles4.xml-p000055002p000104998.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles5.xml-p000105002p000184999.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles6.xml-p000185003p000305000.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles7.xml-p000305002p000465001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles8.xml-p000465001p000665001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles9.xml-p000665001p000925001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles10.xml-p000925001p001325001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles11.xml-p001325001p001825001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles12.xml-p001825001p002425000.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles13.xml-p002425002p003125001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles14.xml-p003125001p003925001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles15.xml-p003925001p004824998.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles16.xml-p004825005p006025001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles17.xml-p006025001p007524997.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles18.xml-p007525004p009225000.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles19.xml-p009225002p011124997.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles20.xml-p011125004p013324998.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles21.xml-p013325003p015724999.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles22.xml-p015725013p018225000.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles23.xml-p018225004p020925000.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles24.xml-p020925002p023725001.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles25.xml-p023725001p026624997.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles26.xml-p026625004p029624976.bz2
wget -c https://dumps.wikimedia.org/enwiki/20150702/enwiki-20150702-pages-articles27.xml-p029625017p047137381.bz2
```

There is a single .bz2 archive available as well but the above might be prone to fewer errors when downloading.

Extract the titles and article bodies into a smaller JSON file for processing:

```bash
$ python app.py get_wikipedia_content title_article_extract.json
```

Pluck meta data from the articles into a passenger statistics file:

```bash
$ python app.py pluk_airport_meta_data title_article_extract.json stats.json
```

Plot the passenger statistics:

```bash
$ deactivate
$ wget http://eoimages.gsfc.nasa.gov/images/imagerecords/55000/55167/earth_lights_lrg.jpg
$ python plot.py render stats.json out.png
$ python plot.py render stats.json out.svg
```

# License

The MIT License (MIT)

Copyright (c) 2015 Mark Litwintschik

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
