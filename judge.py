# from detect import detection_img,show_img
import math

def angle_between_vectors(ax, ay, bx, by):
    dot_product = ax * bx + ay * by
    magnitude_a = math.sqrt(ax**2 + ay**2)
    magnitude_b = math.sqrt(bx**2 + by**2)

    # 防止除零
    if magnitude_a == 0 or magnitude_b == 0:
        raise ValueError("向量长度不能为 0")

    # 夹角的余弦值
    cos_theta = dot_product / (magnitude_a * magnitude_b)
    
    # 防止精度问题超出 acos 定义域
    cos_theta = max(-1.0, min(1.0, cos_theta))

    angle_rad = math.acos(cos_theta)
    angle_deg = math.degrees(angle_rad)

    return angle_deg

def judge_pose(points):
    if len(points.pose_world_landmarks)== 0:
        return None,None
    world_landmarks = points.pose_world_landmarks[0]
    # for i, lm in enumerate(world_landmarks):
    #     print(f"World Landmark {i}: x={lm.x}, y={lm.y}, z={lm.z}, visibility={lm.visibility}, presence={lm.presence}\n")

    ear_l,ear_r = world_landmarks[7],world_landmarks[8]
    ear_m_x,ear_m_y,ear_m_z = (ear_l.x + ear_r.x) / 2,(ear_l.y + ear_r.y) / 2,(ear_l.z + ear_r.z) / 2
    print(f"ear x: {ear_m_x},y: {ear_m_y},z: {ear_m_z}")

    shoulder_l,shoulder_r = world_landmarks[11],world_landmarks[12]
    shoulder_m_x,shoulder_m_y,shoulder_m_z = (shoulder_l.x + shoulder_r.x)/2,(shoulder_l.y + shoulder_r.y)/2,(shoulder_l.z + shoulder_r.z)/2
    print(f"shoulder x: {shoulder_m_x},y: {shoulder_m_y},z: {shoulder_m_z}")

    hip_l,hip_r = world_landmarks[23],world_landmarks[24]
    hip_m_x,hip_m_y,hip_m_z = (hip_l.x + hip_r.x) / 2,(hip_l.y + hip_r.y) / 2,(hip_l.z + hip_r.z) / 2
    print(f"hip x: {hip_m_x},y: {hip_m_y},z: {hip_m_z}")

    knee_l,knee_r = world_landmarks[25],world_landmarks[26]
    knee_m_x,knee_m_y,knee_m_z = (knee_l.x + knee_r.x)/2,(knee_l.y + knee_r.y)/2,(knee_l.z + knee_r.z)/2
    print(f"knee x: {knee_m_x},y: {knee_m_y},z: {knee_m_z}")

    neck_d = angle_between_vectors(ear_m_x-shoulder_m_x,ear_m_y-shoulder_m_y,0,shoulder_m_y)
    print(f"neck_d: {neck_d}")
    if neck_d > 20:
        neck = "front"
    elif neck_d < 0:
        neck = "back"
    else:
        neck = "normal"
    body_d = angle_between_vectors(shoulder_m_x-hip_m_x,shoulder_m_y-hip_m_y,knee_m_x-hip_m_x,0)
    print(f"body_d: {body_d}")
    if body_d > 90+10:
        body = "back"
    elif body_d < 90-10:
        body = "front"
    else:
        body = "normal"
    return neck,body

# img,points = detection_img(f'./img/1.png')
# neck,body = judge_pose(points)
# show_img(img,points)
