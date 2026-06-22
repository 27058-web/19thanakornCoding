print("โปรแกรมคำนวนคะแนนรวมวิชา")

point_Math = int(input("คะแนนวิชาคณิตศาตร์: "))
point_Eng = int(input("คะแนนวิชาอังกฤษ: "))
point_PE = int(input("คะแนนวิชาพลศึกษา: "))

total_point = point_Math + point_Eng + point_PE
print("คะแนนรวม", total_point)
average = total_point / 3
print("คะแนนเฉลี่ยทั้ง3วิชา", average)

if average >= 80:
   print("ดีเยี่ยม100% เก่งจัดๆ")
elif average >= 60:
   print("ผ่าน ผ่านไปเลย")
else:
   print("ควรปรับปรุง นะจะจุ้บๆ")

print("ผู้เขียนโปรแกรม นายธณากร กองตา ม4/4 เลขที่19")