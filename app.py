try:
    import streamlit as st
    import requests
    from bs4 import BeautifulSoup
    import pymongo
    import os
    import logging
    from PIL import Image
    from io import BytesIO
    import zipfile

    logging.basicConfig(filename="scrapper.log", level=logging.INFO)

    def main():
        # Streamlit App Title
        st.title("Image Scraper and Viewer")

        # MongoDB connection setup
        mongo_username = os.getenv('MONGODBUSERNAME')
        mongo_password = os.getenv('MONGODBPASSWORD')

        # Input field for the search query
        query = st.text_input("Enter search query for images (Press Enter or click Search):", on_change=lambda: st.session_state['trigger'](), key='search_query')

        # Initialize session state for triggering search
        if 'trigger' not in st.session_state:
            st.session_state['trigger'] = lambda: None

        def scrape_and_display():
            try:
                if not query:
                    st.error("Please enter a search query.")
                    return

                # Directory to store downloaded images
                save_directory = "images/"
                if not os.path.exists(save_directory):
                    os.makedirs(save_directory)

                # Fake user agent to avoid being blocked by Google
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}

                # Fetch the search results page
                response = requests.get(
                    f"https://www.google.com/search?q={query.replace(' ', '')}&sxsrf=AJOqlzUuff1RXi2mm8I_OqOwT9VjfIDL7w:1676996143273&source=lnms&tbm=isch&sa=X&ved=2ahUKEwiq-qK7gaf9AhXUgVYBHYReAfYQ_AUoA3oECAEQBQ&biw=1920&bih=937&dpr=1#imgrc=1th7VhSesfMJ4M",
                    headers=headers
                )

                # Parse the HTML using BeautifulSoup
                soup = BeautifulSoup(response.content, "html.parser")

                # Find all img tags
                image_tags = soup.find_all("img")

                # Remove the first image tag (often a placeholder)
                if image_tags:
                    del image_tags[0]

                img_data = []
                displayed_images = []
                image_paths = []

                for index, image_tag in enumerate(image_tags[:20]):  # Limit to 20 images
                    image_url = image_tag.get('src')
                    if not image_url:
                        continue

                    # Fetch image data
                    image_data = requests.get(image_url).content

                    # Save image locally
                    file_name = os.path.join(save_directory, f"{query}_{index}.jpg")
                    with open(file_name, "wb") as f:
                        f.write(image_data)
                    image_paths.append(file_name)

                    # Add image data to the list for MongoDB
                    img_data.append({"Index": f"{query}_{index}", "Image": image_data})

                    # Display the image
                    img = Image.open(BytesIO(image_data))
                    displayed_images.append(img)

                # MongoDB insertion
                client = pymongo.MongoClient(f"mongodb+srv://{mongo_username}:{mongo_password}@cluster0.yz3ww.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
                db = client['image_scrap']
                image_col = db['image_scrap_data']
                image_col.insert_many(img_data)

                st.success(f"Scraped and saved {len(img_data)} images successfully!")

                # Create a ZIP file for download
                zip_file_path = os.path.join(save_directory, f"{query}_images.zip")
                with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                    for file_path in image_paths:
                        zipf.write(file_path, os.path.basename(file_path))

                # Provide download link for the ZIP file
                with open(zip_file_path, "rb") as zipf:
                    st.download_button(
                        label="Download All Images as ZIP",
                        data=zipf,
                        file_name=f"{query}_images.zip",
                        mime="application/zip"
                    )
                    
                # Display all images
                st.image(displayed_images, caption=[f"Image {i+1}" for i in range(len(displayed_images))], width=150)


            except Exception as e:
                logging.error(e)
                st.error("An error occurred. Check the logs for details.")

        # Search button
        if st.button("Search"):
            scrape_and_display()

        # Trigger scraping when query is entered
        if st.session_state.get('search_query'):
            scrape_and_display()

    if __name__ == "__main__":
        main()

except ModuleNotFoundError as e:
    if "streamlit" in str(e):
        print("Error: The 'streamlit' module is not installed. Please install it using 'pip install streamlit' and try again.")
    else:
        raise
