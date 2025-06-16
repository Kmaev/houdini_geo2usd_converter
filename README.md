## Houdini Geometry to USD Converter

Demo Presentation:

https://vimeo.com/930979091

### Problem to Solve

Marketplace assets often arrive as geometry files and Mantra shading setups that aren’t USD‑ready. This tool eliminates the need for repetitive manual steps:

- Loading geometry into Houdini  
- Rebuilding shading networks or exporting textures  
- Creating USD scenes with accurate material assignments  

Built with **PySide2**, this tool automates the process by:

1. Extracting metadata  
2. Packaging geometry and material data

   <img width="1459" alt="image" src="https://github.com/user-attachments/assets/e36388da-6de9-4c28-a188-5ef43015ec00" />

3. Reassembling USD scenes with **MaterialX**‑compliant shaders  
4. Offering a UI to browse the generated asset library  
5. Allowing users to import USD templates directly into the scene or save them in the background.  

   <img width="535" alt="image" src="https://github.com/user-attachments/assets/2574a2f9-5a35-49f6-9970-f0dc50b5ac26" />
  
  Current Build Limitation

- This version does *not* use any USD API directly; it relies entirely on Houdini’s LOP-based USD ROPs.  

Future Development Roadmap

- Migrate USD construction to use the full USD API-based pipeline—enabling true headless execution.
