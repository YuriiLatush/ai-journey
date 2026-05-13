rooms = int(input("How many rooms? "))
clean_type = input("Deep or standard? ")

if clean_type == "deep":
    price = rooms * 100
else:
    price = rooms * 60

print("Price: $" + str(price))