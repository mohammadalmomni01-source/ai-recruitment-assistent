import os

JOB_PATH = os.path.join("data", "job_description.txt")


def load_job_description(path=JOB_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


if __name__ == "__main__":
    jd = load_job_description()
    print(jd)
    print("-" * 40)
    print("Characters:", len(jd))