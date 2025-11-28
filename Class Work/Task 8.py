class Cat:
    name = None
    age = None
    isHappy = None
    muhtars = None

    def set_data(self, name, age, isHappy, muhtars):
        self.name = name
        self.age = age
        self.isHappy = isHappy
        self.muhtars = muhtars


cat1 = Cat()
cat = Cat()

cat.set_data('cat1', 10, True, False)
cat1.set_data('cat2', 10, True, True)