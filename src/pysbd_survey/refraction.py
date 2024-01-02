import numpy as np

####################################################################################################
def ray_trace_multiple_angles_times(angles_times, depth_velocity_profile):
    results = []

    for take_off_angle, measured_travel_time in angles_times:
        angle = np.radians(take_off_angle)
        total_time = 0
        total_depth = 0
        total_horizontal_distance = 0

        for i in range(1, len(depth_velocity_profile)):
            depth1, velocity1 = depth_velocity_profile[i - 1]
            depth2, velocity2 = depth_velocity_profile[i]

            delta_depth = depth2 - depth1
            horizontal_distance = delta_depth / np.tan(angle)

            # Path length in the layer
            path_length = np.sqrt(delta_depth**2 + horizontal_distance**2)
            # Time taken to travel this path length
            time_in_layer = path_length / velocity1
            total_time += time_in_layer

            if total_time >= measured_travel_time:
                # Adjust final point based on the time overshot
                overshot_time = total_time - measured_travel_time
                corrected_path_length = path_length - overshot_time * velocity1
                corrected_horizontal_distance = corrected_path_length * np.cos(angle)
                corrected_depth = depth1 + corrected_path_length * np.sin(angle)

                results.append((corrected_depth, total_horizontal_distance + corrected_horizontal_distance))
                break

            total_depth += delta_depth
            total_horizontal_distance += horizontal_distance

            angle = np.arcsin((velocity1 / velocity2) * np.sin(angle))

        if total_time < measured_travel_time:
            # If the loop completes without reaching the travel time, append the final depth and distance
            results.append((total_depth, total_horizontal_distance))

    return results

# # Example usage
# angles_times = [(30, 0.1), (45, 0.15), (60, 0.2)]  # List of (angle, travel time) pairs
# results = ray_trace_multiple_angles_times(angles_times, depth_velocity_profile)

# for i, (depth, distance) in enumerate(results):
#     print(f"Angle {angles_times[i][0]}°, Travel Time {angles_times[i][1]}s: Depth = {depth} meters, Distance = {distance} meters")


####################################################################################################
def ray_trace_to_time(take_off_angle, measured_travel_time, depth_velocity_profile):
    angle = take_off_angle
    total_time = 0
    total_depth = 0
    total_horizontal_distance = 0

    for i in range(1, len(depth_velocity_profile)):
        depth1, velocity1 = depth_velocity_profile[i - 1]
        depth2, velocity2 = depth_velocity_profile[i]

        delta_depth = depth2 - depth1
        horizontal_distance = delta_depth / np.tan(angle)

        # Path length in the layer
        path_length = np.sqrt(delta_depth**2 + horizontal_distance**2)
        # Time taken to travel this path length
        time_in_layer = path_length / velocity1
        total_time += time_in_layer

        if total_time >= measured_travel_time:
            # Adjust final point based on the time overshot
            overshot_time = total_time - measured_travel_time
            corrected_path_length = path_length - overshot_time * velocity1
            corrected_horizontal_distance = corrected_path_length * np.cos(angle)
            corrected_depth = depth1 + corrected_path_length * np.sin(angle)

            return corrected_depth, total_horizontal_distance + corrected_horizontal_distance

        total_depth += delta_depth
        total_horizontal_distance += horizontal_distance

        angle = np.arcsin((velocity1 / velocity2) * np.sin(angle))

    return total_depth, total_horizontal_distance

# Example usage
# measured_travel_time = 0.1  # Example travel time in seconds
# final_depth, final_horizontal_distance = ray_trace_to_time(take_off_angle, measured_travel_time, depth_velocity_profile)

# print(f"Final Depth: {final_depth} meters, Final Horizontal Distance: {final_horizontal_distance} meters")


# def ray_trace_to_time(take_off_angle, measured_travel_time, depth_velocity_profile):
#     angle = np.radians(take_off_angle)
#     ray_path = [(0, 0, 0)]  # Starting at the surface with 0 horizontal distance and 0 time

#     total_time = 0
#     for i in range(1, len(depth_velocity_profile)):
#         depth1, velocity1 = depth_velocity_profile[i - 1]
#         depth2, velocity2 = depth_velocity_profile[i]

#         delta_depth = depth2 - depth1
#         horizontal_distance = delta_depth / np.tan(angle)

#         # Path length in the layer
#         path_length = np.sqrt(delta_depth**2 + horizontal_distance**2)
#         # Time taken to travel this path length
#         time_in_layer = path_length / velocity1
#         total_time += time_in_layer

#         if total_time >= measured_travel_time:
#             # Adjust final point based on the time overshot
#             overshot_time = total_time - measured_travel_time
#             corrected_path_length = path_length - overshot_time * velocity1
#             corrected_horizontal_distance = corrected_path_length * np.cos(angle)
#             corrected_depth = depth1 + corrected_path_length * np.sin(angle)

#             return corrected_depth, total_horizontal_distance + corrected_horizontal_distance

#         total_depth, total_horizontal_distance, _ = ray_path[-1]
#         new_depth = total_depth + delta_depth
#         new_horizontal_distance = total_horizontal_distance + horizontal_distance

#         ray_path.append((new_depth, new_horizontal_distance, total_time))

#         angle = np.arcsin((velocity1 / velocity2) * np.sin(angle))

#     return new_depth, new_horizontal_distance

# Example usage
depth_velocity_profile = [(0, 1500), (100, 1550), (200, 1600)]  # Example profile
take_off_angle = 30  # Degrees
measured_travel_time = 0.1  # Example travel time in seconds
final_depth, final_horizontal_distance = ray_trace_to_time(take_off_angle, measured_travel_time, depth_velocity_profile)

print(f"Final Depth: {final_depth} meters, Final Horizontal Distance: {final_horizontal_distance} meters")
