# Elduende

Scraping new articles from [revistaelduende.com](https://revistaelduende.com)

#### PROCESS
  - Get links from sitemap.xml.Filter updated articles from last 24h.
  - For each updated article, retrieve its fields (title, content, images, author,url, publication date)
  - Upload data to core db, via API

#### PROJECT STRUCTURE
- Project tree
  - data
    - logs
  - config_files
  - modules
  - test

  <br>
  
  **Config.yaml**
    - This file is inside **config_files** folder. Manually create when deployed as .exe
  
  **Logs**
  - Inside data's folder, create logs directory. Inside it, log daily data.

#### DEPLOY IN VIRTUAL MACHINE

- Compile python project with pyinstaller (as .exe file)
- No environment variables such as creds, etc. (if creds, then --add-data="creds.yaml;.")
- Copy folder **_config.yaml_** inside project's root directory  
    - elduende
        - src  
            - elDuendeCrawler.exe
            - config.yaml    
            - other folders (if needed)  
        - elduende.bat  
        
    **Compile**:  
```pyinstaller --onefile main.py -n "elDuendeCrawler"```