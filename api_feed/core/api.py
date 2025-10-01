from ninja import NinjaAPI

api = NinjaAPI(title="api_feed", version="1.0.0", description="API de feed")


@api.get("/")
def get_root(request):
    return {"message": "Hello, World!"}
