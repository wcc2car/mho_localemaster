import os
import sys
import glob
import json
import shutil
import ctypes
import msvcrt
import struct
import datetime
import platform
from typing import Literal
from ctypes import wintypes

try:
    import winreg  # Windows only
except ImportError:
    winreg = None

######################################################################################################
# 全域變數集 (儲存程式全域設定，例如初始遊戲路徑)
class AppConfig:

    def __init__(self):
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):            # PyInstaller 打包後使用 _MEIPASS
            self.initial_path = os.path.dirname(sys.executable)                                  # 打包後自動路徑，可改成執行檔所在路徑
        else:
            self.initial_path = "f:/Marvel Heroes Omega 2.16a Steam/Data/Game/Loco/"             # IDE 開發環境指定路徑

    ver_date = ""                                     # 本程式的版本日期
    creation_time = ""                                # JSON 檔案群的建立時間, 當成辨識碼避雷用
    orig_lang = ""                                    # JSON 的原始 StringMap 語言
    game_ver = ""                                     # 遊戲版本, 有多遊戲版本時避雷  game_version
    base_path = ""                                    #
    game_path = ""                                    # .\{遊戲資料夾}\
    loco_path = ""                                    # .\{遊戲資料夾}\Data\Game\Loco\
    src_lang_path = ""                                # [樣本語言]路徑: .\{遊戲資料夾}\Data\Game\Loco\eng.all\
    dst_lang_path = ""                                # [轉出語言]路徑: .\{遊戲資料夾}\Data\Game\Loco\{dst_lang}\
    src_lang = ""                                     # 選取的[樣本語言]: "eng.all"
    dst_lang = ""                                     # 選取的[轉出語言]: "cht.all'
    dir_bak_path = ""                                 # 保留最近一次lang_dir[備份路徑]

glb_vars = AppConfig()  # [建立 全域變數集]


######################################################################################################
# 訊息表, 有中英雙語言, 自動判斷系統語言, 輸出對應語言訊息. // 執行檔參數: 0=英文, >0=中文 // 函式參數: 訊息代號
#  - mesg 字串支援 %s 和 {ver}, 前者: print(out.msg("msg_idx") % (ver1, ver2...)), 多變數時要 () 包起來
#  - 後者: print(out.msg("msg_idx", ver1="", ver2=""... )),  同 f"{ver1} {ver2}" 規則
class LibraryMsgOutput:

    def __init__(self, force_lang=None):
        self.messages = {
            "err_0": (
                "!! 指定的訊息字串異常 !!",
                "!! Specified message string error !!" ),
            ####[初始化與通用]####################################
            "path_err": (
                "!!! 工作路徑錯誤, 本程式需置於 \\{{遊戲資料夾}}\\Data\\Game\\Loco",
                "!!! Invalid working directory. This program must be placed in \\{{Game Folder}}\\Data\\Game\\Loco"),
            "ok?": (
                "  確定嗎? (Y/N/B/Q): ",
                "  Confirm? (Y/N/B/Q): "),
            "hit_next": (
                "\n--- 請按任意一鍵以繼續 ---",
                "\n--- Press any key to continue ---"),
            "rem_json_lock": (
                "本檔案列出預設 locked 的 strings, 此為 [$var$, #tag#] 的 [var, tag] 對映, 不應修改 (僅供參考)",
                "The file lists the default locked strings, This is the [var, tag] mapping for [$var$, #tag#], Should not be modified (for reference only)"),
            "rem_json_mismatch": (
                "本檔案列出樣本字串檔中未配對的文字標籤 (原廠bug), 應優先修正 (僅供參考)",
                "This file Lists unmatched text tags in the sample StringMap file (original bug), should be fixed first (for reference only)"),
            "rem_json_sample": (
                "本檔案為樣本字串檔的重要取樣, 校對使用. 絕對不可修改內文",
                "This file is a key sample of the string file for verification; do not modify its contents."),
            "rem_audit_log": (
                "本檔案列出 StringMap.json 中[ $ 變數]和[#, #/ 標籤]與原始記錄不符之筆數, 除錯用",
                "Lists entries in StringMap.json where [$ variables] or [#, #/ tags] do not match original records, for debugging"),
            "seq": (
                "流水序號= ",
                "Sequence= "),
            "orig_str": (
                "原始字串= ",
                "OrigString= "),
            "dst_str": (
                "目標字串= ",
                "DestString= "),
            "miss_token": (
                "異常詞元= ",
                "MissTokens= "),
            "NG_json1": (
                "!!! JSON 錯誤 !!!  檔案: {path}",
                "!!! JSON ERROR !!!  File: {path}"),
            "NG_json2": (
                "行數: {line}, 欄位: {col}, 字元位置: {pos}",
                "Line: {line}, Column: {col}, Char: {pos}"),
            "NG_json3": (
                "{marker} 第{i_add1}行: {line_i}",
                "{marker} Line {i_add1}: {lines_i}"),

            ######[主選單]#######################################
            "menu_1": (
                "==== MarvelHeroes Omega 語系大師 v1.0  {date} ====",
                "==== MarvelHeroes Omega LocaleMaster v1.0  {date} ====" ),
            "menu_2": (
                "\t1. 克隆一個新的語言包",
                "\t1. Clone a new languagePack" ),
            "menu_3": (
                "\t2. 字串檔轉出 JSON 文字檔",
                "\t2. Convert Strings to JSON" ),
            "menu_4": (
                "\t3. JSON 文字檔重建字串檔",
                "\t3. Rebuild Strings from JSON" ),
            "menu_5": (
                "\t4. 舊版 JSON 轉為新版 JSON",
                "\t4. Migrate Legacy string JSON" ),
            "menu_6": (
                "\t5. 結束",
                "\t5. Exit"),
            "menu_7": (
                "\n\t請選擇功能(1~5): ",
                "\n\tPlease select a function (1~5): "),
            #####[功能一]########################################
            "A_title": (
                "---- MHO 克隆一個新語言包 (用以翻譯新語言) ----",
                "---- MHO Clone a new language pack (for translating into a new language) ----"),
            "A_src": (
                "1. 選取[樣本語言]: 1.英 2.法 3.德 4.葡萄牙 5.俄 6.西班牙 (1~6): ",
                "1. Select [Sample language]: 1.Eng 2.Fra 3.Deu 4.Por 5.Rus 6.Spa (1~9)"),
            "A_dst": (
                "2. 選取[新語言包]檔名: 7.中 8.日 9.韓 (7~9): ",
                "2. Select [New language pack] file name: 7.Chi 8.Jpn 9.Kor (7~9)"),
            "A_lang_name": (
                "3. 輸入[新語言]名稱 (最多 16 Bytes): ",
                "3. Enter [New language] name (max 16 bytes): "),
            "A_submit1": (
                "\n> 樣本語言: {src},  新語言檔名: {dst},  新語言名稱: {name}",
                "\n> Sample language: {src},  New language pack: {dst},  New language name: {name}"),
            "A_src_err": (
                "\n!!! [樣本語言]錯誤: 異常的 {src_locale}",
                "\n!!! [Sample language] error: invalid {src_locale}"),
            "A_dst_err": (
                "\n!!! [新建語言]備份失敗: {err}",
                "\n!!! [New language] backup failed: {err}"),
            "A_clone_err": (
                "\n!!! [樣本語言]克隆失敗: {err}",
                "\n!!! [Sample language] clone failed: {err}"),
            "A_export": (
                "\n> 開始生成新語言包: ",
                "\n> Generating new language pack: "),
            "A_end": (
                "  (親: 新語言包只是個空殼, 實際上還是 {src_lang}, 記得進行翻譯哦)",
                "  (Surprise! The new language pack is just an empty shell. It’s still {src_lang} inside, so it’s translation time.)"),

            #####[功能二]########################################
            "B_title": (
                "---- MHO 語系字串檔轉出 JSON (用以翻譯/修改字串內文) ----",
                "---- MHO Strings export to JSON (for translation/editing string content) ----"),
            "B_src": (
                "1. 選取[樣本語言]: 1.英 2.法 3.德 4.葡萄牙 5.俄 6.西班牙 7.中 8.日 9.韓 (1~9): ",
                "1. Select [sample language]: 1.Eng 2.Fra 3.Deu 4.Por 5.Rus 6.Spa 7.Chi 8.Jpn 9.Kor (1~9)"),
            "B_dst": (
                "2. 選取[轉出語言]: 1.英 2.法 3.德 4.葡萄牙 5.俄 6.西班牙 7.中 8.日 9.韓 (1~9): ",
                "2. Select [output language]: 1.Eng 2.Fra 3.Deu 4.Por 5.Rus 6.Spa 7.Chi 8.Jpn 9.Kor (1~9)"),
            "B_submit1": (
                "\n> 樣本語言: {src},  轉出語言: {dst}",
                "\n> sample language: {src},  output language: {dst}"),
            "B_src_err": (
                "\n!!! [樣本語言]不存在或缺檔",
                "\n!!! [Sample language] does not exist or is missing files."),
            "B_dst_err": (
                "\n!!! [轉出語言]備份失敗: {err}",
                "\n!!! [Output language] backup failed: {err}"),
            "B_export": (
                "\n> 輸出資料夾: {dst}, 生成檔案: ",
                "\n> Parsing started, generating files:\n  Output folder: {dst}"),
            "B_out_dbg1": (
                " - {dbg_samp} (校正樣本, 不可修改)",
                " - {dbg_samp} (Calibration sample, do not modify)"),
            "B_out_dbg2": (
                " - {dbg_lock} (已鎖定字串清單, 僅供參考)",
                " - {dbg_lock} (Locked string list, reference only)"),
            "B_out_dbg3": (
                " - {dbg_mismatch} (未配對文字標籤清單, 僅供參考)",
                " - {dbg_mismatch} (Unmatched text tag list, reference only)"),
            "B_out_main": (
                " - {main_table} (字串檔主資料表, 不可修改)",
                " - {main_table} (StringMap main table, do not modify)"),
            "B_out_txt": (
                " - {string_txt} (字串檔文字內容, 可編輯字串文字)",
                " - {string_txt} (StringMap text content, editable string content)"),
            #####[功能三]########################################
            "C_title": (
                "---- MHO JSON 文字檔重建字串檔 (生成翻譯/修改的字串檔) ----",
                "---- MHO JSON rebuild to strings (generate translated/modified strings) ----"),
            "C_dst": (
                "1. 選取[目標語言]: 1.英 2.法 3.德 4.葡萄牙 5.俄 6.西班牙 7.中 8.日 9.韓 (1~9): ",
                "1. Select [Target language]: 1.Eng 2.Fra 3.Deu 4.Por 5.Rus 6.Spa 7.Chi 8.Jpn 9.Kor (1~9)"),
            "C_submit1": (
                "\n> 目標語言: {dst_lang}, 重建: {dst_lang}_{{3/7/B/F}}FFFFFFFFFFFFFFF.string",
                "\n> Target language: {dst_lang}, Rebuilding: {dst_lang}_{{3/7/B/F}}FFFFFFFFFFFFFFF.string"),
            "C_submit2": (
                "  - 工作資料夾: {dst_path}\n  - 必備檔案: {main_json}, {string_json}, {samp_json}",
                "  - Working folder: {dst_path}\n  - Required files: {main_json}, {string_json}, {samp_json}"),
            "C_json_chk1": (
                "\n> 檢測 JSON 檔一致性:",
                "\n> Checking JSON consistency:"),
            "C_json_chk2": (
                "  - {jsonfile} 建檔時間: {creat_time}",
                "  - {jsonfile} Created: {creat_time}"),
            "C_json_chk3": (
                "\n!!! JSON 檔案版本 {json_ver} 與當前遊戲版本 {game_ver} 不符",
                "\n!!! JSON version {json_ver} does not match current game version {game_ver}"),
            "C_json_chk4": (
                "!!! JSON 建立時間不一致, 要繼續嗎? (Y/N): ",
                "!!! JSON Creation times do not match. Continue? (Y/N): "),
            "C_src_err": (
                "\n!!! [樣本語言]不存在或缺檔",
                "\n!!! [Sample language] does not exist or is missing files."),
            "C_dst_err": (
                "\n!!! [轉出語言]備份失敗: {err}",
                "\n!!! [Output language] backup failed: {err}"),
            "C_export1": (
                "\n> 生成新字串檔: ",
                "\n> Generating new Strings: "),
            "C_export2": (
                "  - {out}",
                "  - {out}"),
            "C_export3": (
                "  - {dst_lang}.dbg-audit_tokens.log (字串的[$變數,#標籤]校對記錄)",
                "  - {dst_lang}.dbg-audit_tokens.log (String [$vars, #tags] audit log)"),
            "C_stat_err1": (
                "格式錯誤: {part}",
                "Malformed segment: {part}"),
            "C_stat_err2": (
                "無效布林值(限 0,1): {key}={val}",
                "Invalid boolean value (expected 0,1): {key}={val}"),

            #####[功能四]########################################
            "D_title": (
                "---- MHO 舊版本 String_Texts.JSON 轉為新版本 ----",
                "---- Migrate MHO String_Texts.json to New Version  ----"),
            "D_dst": (
                "1. 選取[目標語言]: 1.英 2.法 3.德 4.葡萄牙 5.俄 6.西班牙 7.中 8.日 9.韓 (1~9): ",
                "1. Select [Target language]: 1.Eng 2.Fra 3.Deu 4.Por 5.Rus 6.Spa 7.Chi 8.Jpn 9.Kor (1~9)"),
            "D_submit1": (
                "\n> 目標語言: {dst_lang}, 轉出: {dst_lang}.StringMap.json",
                "\n> Target language: {dst_lang}, Convert: {dst_lang}.StringMap.json"),
            "D_submit2": (
                "  - 工作資料夾: {dst_path}\n  - 必備檔案: {old_json}, {new_json}",
                "  - Working folder: {dst_path}\n  - Required file: {old_json}, {new_json}"),
            "D_submit3": (
                "    (建議先以 [功能 2] 建置全新目標 {dst_lang}.StringMap.json)",
                "    (It is recommended to use [Function 2] first to generate a new target {dst_lang}.StringMap.json)"),
            "D_src_err": (
                "\n!!! 檔案不存在: {file}",
                "\n!!! File does not exist: {file}"),
            "D_diff_err": (
                "\n!!! 字串筆數不相符: 新版本: {new} / 舊版本: {old}",
                "\n!!! String entry count mismatch: New: {new} / Old: {old}"),
            "D_eof_err": (
                "\n!!! 字串異常結束: seq_no:{s_no}, vnt_seq_no:{v_no}",
                "\n!!! Abnormal string termination: seq_no:{s_no}, vnt_seq_no:{v_no}"),
            "D_export1": (
                "\n> 生成新檔案: ",
                "\n> Generating new file: "),
        }
        self.lang_mode = self._detect_language(force_lang)

    @staticmethod
    def _detect_language(force_lang):
        if len(sys.argv) > 1:
            try:
                arg = int(sys.argv[1])
                if arg == 0:
                    return "en"
                elif arg > 0:
                    return "zh"
            except ValueError:
                pass

        if force_lang is not None:
            return "en" if force_lang == 0 else "zh"

        if platform.system() == "Windows" and winreg:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Control Panel\International"
                )
                locale_name, _ = winreg.QueryValueEx(key, "LocaleName")
                winreg.CloseKey(key)

                if "zh-TW" in locale_name or "zh_Hant" in locale_name:
                    return "zh"
            except OSError:
                pass
        return "en"

    def msg(self, msg_key, **kwargs):
        lang_index = 0 if self.lang_mode == "zh" else 1
        lib_msg = self.messages.get(msg_key)

        if not lib_msg:
            error_msg = self.messages["err_0"][lang_index]
            return f"{error_msg} ({msg_key})"

        try:
            return lib_msg[lang_index].format(**kwargs)
        except KeyError as e:
            return f"[FORMAT ERROR] missing key: {e} in {msg_key}"

out = LibraryMsgOutput()


######################################################################################################
# 檢測 Marvel Heroes Omega 遊戲是否存在 // 無參數  // 無回傳 : 結果均在 class 變數
class MarvelHeroesDetector:

    def __init__(self):
        self.game_path = ""          # -遊戲路徑
        self.loco_path = ""          # -遊戲語言包路徑
        self.game_exe_path = None    # -執行檔名路徑
        self.game_version = None     # -檔案版本 FileVersion
        self.game_exists = False     # -遊戲存在旗標
        self._detect_game(glb_vars.initial_path)

    def _detect_game(self, path):
        arch_folder = "Win64" if "PROGRAMFILES(X86)" in os.environ else "Win32"
        game_root = os.path.abspath(os.path.join(path, "..", "..", ".."))

        exe_pattern = os.path.join(
            game_root,
            "UnrealEngine3",
            "Binaries",
            arch_folder,
            "MarvelHeroes*.exe"
        )

        exe_list = glob.glob(exe_pattern)
        if exe_list:
            self.game_exe_path = exe_list[0]
            versions = self._get_explorer_style_version(self.game_exe_path)
            self.game_version = versions.get("Explorer_FileVersion")

        lang_list = ["eng", "fra", "deu", "por", "rus", "spa"]

        locale_exist = all(
            os.path.isfile(os.path.join(path, f"{lang}.all.locale"))
            for lang in lang_list
        )

        all_exist = all(
            os.path.isdir(os.path.join(path, f"{lang}.all"))
            for lang in lang_list
        )

        self.game_exists = bool(self.game_exe_path) and all_exist and locale_exist
        if self.game_exists:
            self.game_path = game_root
            self.loco_path = path

    @staticmethod
    def _get_explorer_style_version(file_path):
        version_dll = ctypes.WinDLL("version.dll")
        size = version_dll.GetFileVersionInfoSizeW(file_path, None)
        if not size:
            return {"Explorer_FileVersion": None}

        buffer = ctypes.create_string_buffer(size)
        version_dll.GetFileVersionInfoW(file_path, None, size, buffer)

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD),
                ("dwProductVersionLS", wintypes.DWORD),
            ]

        raw_ptr = ctypes.c_void_p()
        fixed_len = wintypes.UINT()
        binary_file_version = None

        if version_dll.VerQueryValueW(buffer, "\\", ctypes.byref(raw_ptr), ctypes.byref(fixed_len)):
            fixed_ptr = ctypes.cast(raw_ptr, ctypes.POINTER(VS_FIXEDFILEINFO))
            f = fixed_ptr.contents
            binary_file_version = "{}.{}.{}.{}".format(
                f.dwFileVersionMS >> 16, f.dwFileVersionMS & 0xFFFF,
                f.dwFileVersionLS >> 16, f.dwFileVersionLS & 0xFFFF
            )

        return {
            "Explorer_FileVersion": binary_file_version
        }


###################### [以上是類別] ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# 檢查工作路徑與設定路徑
def init_and_check():
    mho = MarvelHeroesDetector()                      # [建立 遊戲軟體 物件]

    if not mho.game_exists:                           # 程式是否置於正確資料夾? ".\遊戲資料夾\\Data\Game\Loco\"
        print(out.msg("path_err"))
        pause(out.msg("hit_next"))
        return False

    glb_vars.ver_date = datetime_string(1)            # 此程式的編修日期: 年-月-日
    glb_vars.game_ver = mho.game_version
    glb_vars.game_path = mho.game_path
    glb_vars.loco_path = mho.loco_path

    return True


###########################################################################################
# 輸出時間字串, 依指定格式 // 參數如下表, 由 0~7 .
def datetime_string(index: int = 0) -> str:

    _FORMATS = (
        "%Y-%m-%d %H:%M:%S",   # 0. 日期 時間
        "%Y-%m-%d",            # 1. 日期
        "%H:%M:%S",            # 2. 時:分:秒
        "%H:%M:%S.%f",         # 3. 時:分:秒.微秒
        "%Y-%m-%d_%H-%M-%S",   # 4. 年-月-日_時-分-秒, 當檔名使用
        "%Y-%m-%d_%H%M",       # 5. 年-月-日_時分, 當檔名使用
        "%m-%d_%H%M",          # 6. 月-日_時分, 當檔名使用
        "%m%d_%H%M%S",         # 7. 月日_時分秒, 當檔名使用
    )

    try:
        fmt = _FORMATS[index]
    except IndexError:
        raise ValueError(f"無效的日期時間格式索引: {index}")

    return datetime.datetime.now().strftime(fmt)


###############################################################################################
# 判斷檔案是否存在. // 參數: "檔名"  // 回傳值: 不存在=False , 存在=True
def check_file_exists(filename):
    if os.path.isfile(filename):
        return True                   # 檔案存在
    else:
        return False                  # 檔案不存在


###############################################################################################
# 清除螢幕
def clear_screen():
    in_pycharm = os.environ.get("PYCHARM_HOSTED") == "1"     # 偵測是否在 PyCharm console

    if in_pycharm:
        print("\n" * 24)                                     # PyCharm console 不支援 cls / clear，使用多行換行模擬 cls
    else:
        os.system('cls' if os.name == 'nt' else 'clear')     # 系統終端機


######################################################################################################
# 輸入一個字元, 等按 enter, 限指定的按鍵. // 參數= message: 提示訊息, allowed_keys: 限用字元, 例如 "AaBb123+"
def input_one_letter(message: str, allowed_keys: str) -> str:
    allowed = set(allowed_keys)

    while True:
        buff = input(message).strip()

        if len(buff) == 1 and buff in allowed:
            return buff


######################################################################################################
# 輸入一個字元, 限指定的按鍵. 不等 Enter // 參數= message: 提示訊息, allowed_keys: 限用字元,忽略大小寫. 例如 "AbC123+"
#                                    // 特輸鍵與混用: allowed_keys={ "Enter","ESC","F1","ABC123+-*/" }
def get_key(message: str, allowed_keys: str):
    allowed_set = {c.lower() for c in allowed_keys}
    print(message, end="", flush=True)

    while True:
        key = msvcrt.getch()

        if key in (b'\x00', b'\xe0'):
            key = msvcrt.getch()

            if key == b';':
                k = "F1"
            elif key == b'<':
                k = "F2"
            elif key == b'=':
                k = "F3"
            elif key == b'>':
                k = "F4"
            elif key == b'?':
                k = "F5"
            elif key == b'@':
                k = "F6"
            elif key == b'A':
                k = "F7"
            elif key == b'B':
                k = "F8"
            elif key == b'C':
                k = "F9"
            elif key == b'D':
                k = "F10"
            elif key == b'E':
                k = "F11"
            elif key == b'F':
                k = "F12"
            else:
                continue

        else:
            try:
                k = key.decode("utf-8")
            except UnicodeDecodeError:
                continue

        if k == "\x1b":
            k = "ESC"

        if k in ("\r", "\n"):
            k = "ENTER"

        if k.lower() in allowed_set or k in allowed_set:
            print()                                             # 換行
            return k


######################################################################
# 限制輸入byte數, UTF8 友善的 input. 參數: prompt=訊息, max_bytes=最大字數 // 回傳: 輸入 byte數, 輸入字串
def limited_input_bytes(prompt="", max_bytes=16):
    s = input(prompt)
    data = s.encode('utf-8')

    if len(data) <= max_bytes:
        return len(data), s

    cut = data[:max_bytes]
    while True:
        try:
            result = cut.decode('utf-8')
            break
        except UnicodeDecodeError:
            cut = cut[:-1]

    return len(cut), result


#########################################################################
# 按下任一鍵繼續 (CMD Pause)
def pause(msg: str = "Press any key to continue..."):
    print(msg, end="", flush=True)
    msvcrt.getch()                                      # 讀取一個鍵，不會顯示


#########################################################################
# 選擇數字 轉換 語系檔名. 參數: 1~9 字串. 回傳: "eng.all"
def select_to_lang_set(n: str, target: Literal["src", "dst"]="src") -> str:
    mapping = {
        "1": "eng.all",
        "2": "fra.all",
        "3": "deu.all",
        "4": "por.all",
        "5": "rus.all",
        "6": "spa.all",
        "7": "chi.all",
        "8": "jpn.all",
        "9": "kor.all",
    }

    t_lang = mapping[n]
    t_lang_path = os.path.join(glb_vars.loco_path, t_lang)

    prefix = "src" if target == "src" else "dst"
    setattr(glb_vars, f"{prefix}_lang", t_lang)                      # 設定 glb_vars.src_lang, glb_vars.dst_lang
    setattr(glb_vars, f"{prefix}_lang_path", t_lang_path)            # 設定 glb_vars.src_lang_path, glb_vars.dst_lang_path

    return t_lang


#########################################################################
# Func2: 讀取位元處理
def read_u64(buf, offset):
    return int.from_bytes(buf[offset:offset+8], "little")

def read_u32(buf, offset):
    return int.from_bytes(buf[offset:offset+4], "little")

def read_u16(buf, offset):
    return int.from_bytes(buf[offset:offset+2], "little")


###########################################################
# Func3: 寫入位元處理
def write_u16(v): return struct.pack("<H", v)
def write_u32(v): return struct.pack("<I", v)
def write_u64(v): return struct.pack("<Q", v)


########################################################################
# 檢查 lang.locale 和 .\lang\ 是否存在. lang: "eng.all", dst:"dir/file/both", need_bak:True/False. 回傳: TRue/False, err_msg/None
def check_lang_pack(lang="eng.all", dst=Literal["file", "dir", "both"], need_bak=True):

    base = glb_vars.loco_path
    file_path = os.path.join(base, f"{lang}.locale")
    dir_path = os.path.join(base, lang)

    file_ok = os.path.isfile(file_path)
    dir_ok = False

    if dst in ("dir", "both"):
        if os.path.isdir(dir_path):
            required = [
                f"{lang}_3FFFFFFFFFFFFFFF.string",
                f"{lang}_7FFFFFFFFFFFFFFF.string",
                f"{lang}_bFFFFFFFFFFFFFFF.string",
                f"{lang}_fFFFFFFFFFFFFFFF.string",
            ]
            dir_ok = all(os.path.isfile(os.path.join(dir_path, f)) for f in required)

    if dst == "file":
        ok = file_ok
    elif dst == "dir":
        ok = dir_ok
    else:
        ok = file_ok and dir_ok

    if need_bak:
        try:
            if file_ok and dst in ("file", "both"):
                shutil.move(file_path, f"{file_path}.{datetime_string(7)}")

            if dir_ok and dst in ("dir", "both"):
                glb_vars.dir_bak_path = f"{dir_path}.{datetime_string(7)}"          # 記錄上一次使用的 dir 備份路徑, 重要機置
                shutil.move(dir_path, glb_vars.dir_bak_path)

        except (OSError, IOError) as e:
            return ok, str(e)

    return ok, None


##################################################################
# clone {src_lang} to {dst_lang} , 包含 4 個 StringMap .string
def clone_string_map():
    try:
        src_lang = glb_vars.src_lang
        dst_lang = glb_vars.dst_lang
        src_path = glb_vars.src_lang_path
        dst_path = glb_vars.dst_lang_path

        shards = [
            "3FFFFFFFFFFFFFFF",
            "7FFFFFFFFFFFFFFF",
            "BFFFFFFFFFFFFFFF",
            "FFFFFFFFFFFFFFFF"
        ]

        os.makedirs(dst_path, exist_ok=True)
        for shard in shards:
            src_file = os.path.join(
                src_path,
                f"{src_lang}_{shard}.string"
            )

            dst_file = os.path.join(
                dst_path,
                f"{dst_lang}_{shard}.string"
            )

            shutil.copyfile(src_file, dst_file)
            print(f"  - {dst_file}")
        return True, None

    except Exception as e:
        return False, str(e)


#############################################################################
# 讀 Json 檔時進行偵錯, 與明白報錯
def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(out.msg("NG_json1", path=path))
        print(out.msg("NG_json2", line=e.lineno, col=e.colno, pos=e.pos))
        print("-" * 60)

        lines = raw.splitlines()
        start = max(0, e.lineno - 3)
        end = min(len(lines), e.lineno + 1)

        for i in range(start, end):
            marker = ">>" if (i + 1) == e.lineno else "  "
            print(out.msg("NG_json3", marker=marker, i_add1=(i+1), line_i=lines[i]))
        print("-" * 60)
        return None