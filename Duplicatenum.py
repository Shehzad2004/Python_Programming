numbers = [1,2,2,3,1,4,5,5,6]
duplicates = []
for num in numbers:
    if numbers.count(num) > 1 and num not in duplicates:
        duplicates.append(num)
        print(duplicates)
        