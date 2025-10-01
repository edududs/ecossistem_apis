from ninja import NinjaAPI

api = NinjaAPI(title="API de produtos", version="1.0.0", description="API de produtos")


@api.get("/")
def get_root(request):
    return {"message": "Hello, World!"}
