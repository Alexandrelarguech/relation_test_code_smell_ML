# Vérifier ce qu'on a dans tsdetect_fixed
with open("../dataset/tsdetect_fixed/commons-lang.csv", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 3: break
        print(repr(line.strip()))