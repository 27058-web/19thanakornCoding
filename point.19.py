point1=int(input("คะแนนวิชา1: "))
point2=int(input("คะแนนวิชา2: "))
point3=int(input("คะแนนวิชา3: "))

total = point1 + point2 + point3
average = total / 3
print("คะแนนรววม", total)
print("คะแนนเฉลี่ย=" , average )
 
if average >= 80:
   print("ดีเยี่ยม")
elif average >= 60:
   print("ผ่าน")
else:
   print("ควรปรับปรุง")