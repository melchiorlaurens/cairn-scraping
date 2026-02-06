import scrapy


class OuvrageItem(scrapy.Item):
    title = scrapy.Field()
    subtitle = scrapy.Field()
    authors = scrapy.Field()
    collection = scrapy.Field()
    editeur = scrapy.Field()
    date_parution = scrapy.Field()
    date_mise_en_ligne = scrapy.Field()
    pages = scrapy.Field()
    price = scrapy.Field()
    description = scrapy.Field()
    isbn = scrapy.Field()
    theme = scrapy.Field()
    image_url = scrapy.Field()
    url = scrapy.Field()
    doc_id = scrapy.Field()
