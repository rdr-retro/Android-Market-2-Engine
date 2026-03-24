import os
import io
from pyaxmlparser import APK
from PIL import Image

def get_developer(apk):
    try:
        cert = apk.get_certificate(apk.get_signature_name())
        if cert:
            subject = cert.subject.native
            return subject.get("common_name") or subject.get("organization_name") or ""
    except:
        pass
    return ""

def save_icon(apk, filename):
    try:
        icon_data = apk.icon_data
        if icon_data:
            img = Image.open(io.BytesIO(icon_data))
            # Resize by 0.5
            new_size = (int(img.width * 0.5), int(img.height * 0.5))
            img = img.resize(new_size, Image.LANCZOS)
            
            icon_filename = filename.replace(".apk", ".png")
            img.save(icon_filename, "PNG")
            return icon_filename
    except Exception as e:
        print(f"Error saving icon for {filename}: {e}")
    return ""

def get_apk_info(apk_path):
    try:
        apk = APK(apk_path)
        icon_name = save_icon(apk, os.path.basename(apk_path))
        return {
            "filename": os.path.basename(apk_path),
            "name": apk.application or os.path.basename(apk_path).replace(".apk", ""),
            "developer": get_developer(apk),
            "package": apk.package,
            "version_name": apk.version_name,
            "min_sdk": apk.get_min_sdk_version(),
            "target_sdk": apk.get_target_sdk_version(),
            "min_android": sdk_to_android(apk.get_min_sdk_version()),
            "icon_name": icon_name
        }
    except Exception as e:
        return {"filename": os.path.basename(apk_path), "error": str(e)}

def sdk_to_android(sdk_version):
    sdk_map = {
        "1": "1.0", "2": "1.1", "3": "1.5", "4": "1.6",
        "5": "2.0", "6": "2.0.1", "7": "2.1",
        "8": "2.2", "9": "2.3", "10": "2.3.3",
        "11": "3.0", "12": "3.1", "13": "3.2",
        "14": "4.0", "15": "4.0.3", "16": "4.1",
        "17": "4.2", "18": "4.3", "19": "4.4",
        "21": "5.0", "22": "5.1", "23": "6.0",
        "24": "7.0", "25": "7.1", "26": "8.0",
        "27": "8.1", "28": "9.0", "29": "10", "30": "11",
        "31": "12", "32": "12L", "33": "13", "34": "14", "35": "15"
    }
    return sdk_map.get(str(sdk_version), f"{sdk_version}")

def main():
    directory = "."
    output_file = "apks.txt"
    apk_files = [f for f in os.listdir(directory) if f.endswith(".apk")]
    
    if not apk_files:
        print("No se encontraron archivos APK en el directorio.")
        return

    results = []
    
    for apk_file in sorted(apk_files):
        info = get_apk_info(apk_file)
        if "error" in info:
            print(f"Error procesando {apk_file}: {info['error']}")
            continue
        
        # Format block as requested by user
        block = [
            f"name={info['name']}",
            f"developer={info['developer']}",
            "starts=",
            f"iconname=https://raw.githubusercontent.com/rdr-retro/Android-Market-2-Engine/main/{info['icon_name']}",
            "screenshot1=c1.png",
            "screenshot2=c2.png",
            "screenshot3=c3.png",
            "category=apps",
            f"minandroid={info['min_android']}",
            f"appversion={info['version_name']}",
            f"package=https://raw.githubusercontent.com/rdr-retro/Android-Market-2-Engine/main/{info['filename']}",
            "description=",
            "verify=on",
            "type=recommended"
        ]
        results.extend(block)
        results.append("") # Empty line between apps

    # Print to console and save to file
    with open(output_file, "w", encoding="utf-8") as f:
        for line in results:
            print(line)
            f.write(line + "\n")
    
    print(f"\nResultados guardados en: {output_file}")

if __name__ == "__main__":
    main()
