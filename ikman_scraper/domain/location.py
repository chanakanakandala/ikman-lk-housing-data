class Location:
    def __init__(self, loc_id, name, slug):
        self.id = loc_id
        self.name = name
        self.slug = slug

    def __repr__(self):
        return f"Location(id={self.id}, name={self.name}, slug={self.slug})"
