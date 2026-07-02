import random
number = random.randint(1,100)
n = 0

print("ลองทายดูสิ")

while n != number:
    n = int(input("ใส่เลขที่ทาย: "))
    if    n < number:
        print("น้อยเกินไปจ้า")
    elif n > number:
        print("มากเกินไป")
    else:
        print("ถูกต้องแล้วครับ")