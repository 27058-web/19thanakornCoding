speedcar =int(input("ความเร็วของรถ"))

if speedcar <= 80:
   print("ปลอดภัย")
elif speedcar <= 100:
   print("เตือน")
elif speedcar <= 120:
   print("เสี่ยงถูกปรับ")
else:
   print("ผิดกฎหมายปรับทันที")