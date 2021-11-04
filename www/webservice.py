import tornado.ioloop
import tornado.web

import main


class OrderHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("./views/orders.html", orders=main.get_orders())


class ClearOrderHandler(tornado.web.RequestHandler):
    def post(self):
        main.clear_orders()
        self.redirect("/orders")


class PullOrderHandler(tornado.web.RequestHandler):
    def post(self):
        main.pull_orders()
        self.redirect("/orders")


class InventoryHandler(tornado.web.RequestHandler):
    def get(self, inventory):
        pass


if __name__ == "__main__":
    app = tornado.web.Application([
        (r"/orders", OrderHandler),
        (r"/orders/clear", ClearOrderHandler),
        (r"/orders/pull", PullOrderHandler),

        (r"/inventory/(.*)", InventoryHandler),
    ], debug=True)
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
