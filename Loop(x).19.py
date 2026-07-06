print("โปรแกรมแม่สูตรคูณ")
print("แม่สูตรคูณ56 สุดโหด")

stat =int(input("แม่เริ่มต้น= "))
end = int(input("แม่สุดท้าย= "))

for i in range(stat , end +1):
    print("แม่สูตรคูณแม่",  i )
    for loop in range (1,13):
     print(i, "x", loop , "=" ,i*loop)

print("จัดทำโดย นายธณากร กองตา ม.4/4 เลขที่ 19")