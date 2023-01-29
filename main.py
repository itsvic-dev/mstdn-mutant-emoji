import os
import json
import requests
import mstdnemoji
import multiprocessing


def get_session_id():
    config = {}
    if os.path.exists(".config.json"):
        with open(".config.json") as file:
            config = json.load(file)
            if "session_id" in config:
                return config['session_id']
    session_id = input("Enter Session ID: ")
    with open(".config.json", 'w+') as file:
        print("Saving for later use.")
        config['session_id'] = session_id
        json.dump(config, file)
    return session_id


def get_instance_domain():
    config = {}
    if os.path.exists(".config.json"):
        with open(".config.json") as file:
            config = json.load(file)
            if "instance" in config:
                return config['instance']
    instance_domain = input("Enter instance domain: ")
    with open(".config.json", 'w+') as file:
        print("Saving for later use.")
        config['instance'] = instance_domain
        json.dump(config, file)
    return instance_domain


def threaded_upload(instance: str, base_session: requests.Session, directory: str, emoji_list: list[str]):
    session = requests.Session()
    session.cookies = base_session.cookies.copy()
    client = mstdnemoji.AdminClient(instance, session)
    for file in emoji_list:
        filename = os.path.splitext(file)[0]
        print(f"Uploading emoji {filename}")
        client.upload_emoji(os.path.join(directory, file), filename)


def upload():
    if not os.path.exists("mtnt_2022.12_masto/emoji"):
        print("Are you sure you extracted the 'mtnt_2022.12_masto.zip' archive into 'mtnt_2022.12_masto'?")
    for directory, _, files in os.walk("mtnt_2022.12_masto/emoji"):
        files.sort()
        print("The upload can be split into batches. This will speed the upload up a lot, though it may wreak havoc "
              "on your network. To stay on the safe side, you can keep this number low (around 1-4).")
        batch_count = int(input("How many batches should the upload be split into? "))
        count = round(len(files) / batch_count)
        batches = [files[i*count:i*count+count] for i in range(batch_count)]
        processes = []
        for batch in batches:
            process = multiprocessing.Process(target=threaded_upload, args=(instance, session, directory, batch))
            processes.append(process)
            process.start()
        for process in processes:
            process.join()


def delete():
    client = mstdnemoji.AdminClient(instance, session)
    pages = client.get_emoji_page_count()
    for i in range(pages):
        print(f"Deleting emoji page {i+1}/{pages}")
        client.delete_emoji_page()


if __name__ == "__main__":
    instance = get_instance_domain()
    session = requests.Session()
    session.cookies.set('_session_id', get_session_id())
    print("What do you want to do?")
    print("u: Upload Mutant emojis")
    print("d: Delete Mutant emojis")
    choice = input("> ").lower()
    if choice == "u":
        upload()
    if choice == "d":
        delete()
    else:
        print("Invalid choice!")
        exit(1)
