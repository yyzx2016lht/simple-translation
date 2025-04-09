def find_power_of_3_with_rearrangement():
    """查找一个3的方幂，使其数字重排后形成另一个3的方幂"""
    # 用字典存储每个3的方幂的排序后的数字
    powers_dict = {}  # 键：排序后的数字，值：对应的3的方幂
    power = 3  # 从3^1开始
    
    # 设置一个合理的上限
    max_exponent = 50  # 可以根据需要调整
    
    for i in range(1, max_exponent + 1):
        # 将当前3的方幂的数字按升序排序
        sorted_digits = ''.join(sorted(str(power)))
        
        # 检查是否已经存在具有相同数字的3的方幂
        if sorted_digits in powers_dict:
            # 找到了满足条件的方幂对
            original_power = powers_dict[sorted_digits]
            return original_power, power
        else:
            # 记录当前方幂
            powers_dict[sorted_digits] = power
        
        # 计算下一个3的方幂
        power *= 3
    
    return None

# 查找符合条件的3的方幂
result = find_power_of_3_with_rearrangement()

if result:
    power1, power2 = result
    print(f"找到了符合条件的3的方幂对：")
    print(f"{power1} 和 {power2}")
    print(f"它们都是3的方幂，且一个是另一个数字的重排")
else:
    print("在给定范围内没有找到符合条件的3的方幂")