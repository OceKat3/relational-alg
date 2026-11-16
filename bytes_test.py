b = bytearray('\xFFbcd', encoding="utf-8")

print(int.from_bytes(b[2:]))
print(int.from_bytes(b[1:]))
print(int.from_bytes(b, signed=False))
print(int.from_bytes(b, signed=True))

print(str(b, encoding='utf-8'))


a = 123
a.to_bytes()