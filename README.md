# hyperlyse

Hyperspectral Image Analysis tool

---

See directory <code>doc</code> for documentation.

---
## Changelog

### v1.3
* R009 brightness adjustment slider for visualization image
* R010 UI element for y-range
* configuration in config.json
* semitransparent markers 
* R011 define custom spectral range (x-axis) used for all comparison operations (with UI element)
* R012 select spectrum by rectangle (average)
* R013 new database architecture
  - DETAILED REQUIREMENTS 
    - load and save, portable db format 
    - select, display and compare specific DB spectrum
    - extended fields/metadata for database spectra
    - image of source material
  - SOLUTION
    - based on file system
    - for each spectrum, store:
      - jcamp-dx file with spectrum data and metadata
      - png image with visualization of source
    - load database -> recursivly parse arbitryry folder, or load single file
    - save to database -> just save anywhere
    - delete from database -> delete from filesystem
    - portable -> just copy filesystem
    - new fields and where they are stored in jcamp-dx:
      - name/id ==> ##TITLE
      - origin (e.g. name of color poster or manuscript) ==> ##TITLE
      - original HSI file ==> ##SOURCE REFERENCE
      - rectangle of measurement ==> ##SOURCE REFERENCE
      - measurement device ==> ##SPECTROMETER/DATASYSTEM
      - pigment intensity (light, medium, dark) ==> ##SAMPLE DESCRIPTION
* in the process: lots of internal refactoring

### v1.2
* Migration to Qt6 (also updated the other python packages)
* Zooming: Slider instead of combo box - smaller increments
* R005 higher zoom level by default (--> make windows larger upon startup, make image fill whole area
* R006 no automatic scaling of y-axis (graph)
* R008 support for general envi files (not only from Specim IQ)
* R008.A comparison of spectra with different bands
* R007 PCA - without much user control. might be added on request.

### v1.1
* R001 export image with marked samplepoint together with spectrum
* R002 zoom (for precise point selection)
* R003 export to JCAMP format
* R004 make spectra exports perfectly compatible with exports from SpecimIQ Studio
* spectral databases and spectra comparison features (experimental)
* advanced image view modes

### open feature requests
(none)
    
---

## Building
for python packages, see requirements.txt

**building with pyinstaller currently only works up to python 3.9**

for building with pyinstaller on Windows, cd to /hyperlyse/ and run build.bat