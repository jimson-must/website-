# Student Performance Analyzer

def get_comment(average):
    """Return a comment based on the average mark."""
    if average >= 90:
        return "Outstanding performance! Keep it up."
    elif average >= 80:
        return "Excellent work. Very strong results."
    elif average >= 70:
        return "Good performance. Solid effort."
    elif average >= 60:
        return "Fair performance. There's room for improvement."
    elif average >= 50:
        return "Average performance. Needs more focus."
    else:
        return "Poor performance. Serious improvement needed."


def main():
    print("=" * 55)
    print("          STUDENT PERFORMANCE SYSTEM")
    print("=" * 55)

    # Ask for number of students
    while True:
        try:
            num_students = int(input("\nHow many students do you want to enter? "))
            if num_students > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Ask for number of courses
    while True:
        try:
            num_courses = int(input("How many courses/subjects? "))
            if num_courses > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Get course names
    courses = []
    print("\nEnter the names of the courses:")
    for i in range(num_courses):
        course = input(f"  Course {i+1}: ").strip()
        courses.append(course if course else f"Course {i+1}")

    students = []   # Will store dictionaries for each student

    # Collect data for each student
    for i in range(num_students):
        print("\n" + "-" * 45)
        print(f"Student {i+1} of {num_students}")
        print("-" * 45)

        name = input("Enter student name: ").strip()
        if not name:
            name = f"Student {i+1}"

        marks = []
        print(f"\nEnter marks for {name}:")
        for course in courses:
            while True:
                try:
                    mark = float(input(f"  {course}: "))
                    if 0 <= mark <= 100:
                        marks.append(mark)
                        break
                    else:
                        print("    Mark must be between 0 and 100.")
                except ValueError:
                    print("    Please enter a valid number.")

        average = sum(marks) / len(marks)

        students.append({
            "name": name,
            "marks": marks,
            "average": average
        })

    # ========== DISPLAY RESULTS ==========
    print("\n\n" + "=" * 55)
    print("               PERFORMANCE REPORT")
    print("=" * 55)

    # Show all students
    print("\nAll Students Performance:\n")
    print(f"{'No.':<5}{'Name':<20}{'Average':<12}{'Comment'}")
    print("-" * 55)

    for idx, student in enumerate(students, 1):
        comment = get_comment(student["average"])
        print(f"{idx:<5}{student['name']:<20}{student['average']:<12.2f}{comment}")

    # Find best and worst performers
    best = max(students, key=lambda s: s["average"])
    worst = min(students, key=lambda s: s["average"])

    print("\n" + "=" * 55)
    print("               TOP & BOTTOM PERFORMERS")
    print("=" * 55)

    # Best performer
    print("\n BEST PERFORMER")
    print(f"   Name     : {best['name']}")
    print(f"   Average  : {best['average']:.2f}")
    print(f"   Comment  : {get_comment(best['average'])}")
    print("   Marks    :")
    for course, mark in zip(courses, best["marks"]):
        print(f"     - {course}: {mark}")

    # Worst performer
    print("\n LAST (WORST) PERFORMER")
    print(f"   Name     : {worst['name']}")
    print(f"   Average  : {worst['average']:.2f}")
    print(f"   Comment  : {get_comment(worst['average'])}")
    print("   Marks    :")
    for course, mark in zip(courses, worst["marks"]):
        print(f"     - {course}: {mark}")

    # Extra motivation messages
    print("\n" + "=" * 55)
    print("Special Comments:")
    print(f"  Congratulations to {best['name']} for the best performance!")
    print(f"  {worst['name']} is encouraged to work harder and seek help where needed.")
    print("=" * 55)
    print("\nThank you for using the Student Performance System!")


if __name__ == "__main__":
    main()