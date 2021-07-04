import tornado.ioloop
import tornado.web
import tornado.autoreload


class InventoryHandler(tornado.web.RequestHandler):
    def get(self, inventory):
        pass



if __name__ == "__main__":
    app = tornado.web.Application([
        (r"/inventory/(.*)", InventoryHandler),
    ], debug=True)
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
