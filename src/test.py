from multiprocessing import Pool
import time


# def a():
#     for i in range(1,10):
#         time.sleep(2)
#         print(i)

# def b():
#     with Pool(5) as p:
#         p.apply_async(a)
#     return 'hola'


a= 'https://example.com'
a = a[8:]
print(a)
# print(b())