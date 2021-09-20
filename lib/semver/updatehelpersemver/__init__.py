def cmp_version(version_a, version_b):
    version_a_list = process_version(version_a[0])
    version_b_list = process_version(version_b[0])
    for i in range(min(len(version_a_list), len(version_b_list))):
        try:
            result = compare(version_a_list[i], version_b_list[i])
            if result != 0:
                return result
        except TypeError:
            result = compare(str(version_a_list[i]), str(version_b_list[i]))
            if result != 0:
                return result
    
    return compare(len(version_a_list), len(version_b_list))


def process_version(version):
    components = version.split('.')
    result = []
    for c in components:
        try:
            i = int(c)
        except ValueError:
            i = c
        result.append(i)
    
    return result


def compare(a, b):
    if a > b:
        return 1
    elif a < b:
        return -1
    return 0
