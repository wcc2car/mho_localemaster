import re
import ast

from collections import Counter
from library_share import *


#######################################################################################################
# 資料結構: 存放 4 個 String Mapping file 解析結果
class StringMap:
    def __init__(self):
        self.creation_time: str = ""
        self.original_language: str = ""
        self.file_version: str = ""
        self.header:str = ""

        self.entries_num: dict[str, int] = {
            "3": 0,
            "7": 0,
            "B": 0,
            "F": 0,
        }

        self.entries: list[dict] = []

    ### Entry ########################################################################
    def add_entry(self, uid: int, var_num: int = 0, flags_prod: int = 0, offset: int = 0):
        entry = {
            "seq_no": len(self.entries) + 1,
            "id": uid,
            "var_num": var_num,
            "flags_prod": flags_prod,
            "offset": offset,
            "status": {
                "lock": False,
                "no_audit": False,
                "dollar": 0,
                "hash": 0,
                "hash_slash": 0,
            },
            "string": "",
            "string_vnts": [],
        }

        self.entries.append(entry)
        return entry

    #### C-string decode (ENTRY) ##############################################
    def add_string(self, entry: dict, blob: bytes):
        start = entry["offset"]

        end = blob.find(b"\x00", start)
        if end == -1:
            raise ValueError(f"invalid c-string at offset {start}")

        entry["string"] = blob[start:end].decode("utf-8")
        return entry["string"]

    #### Entry lookup #########################################################
    def get_entry(self, seq_no: int):
        if 1 <= seq_no <= len(self.entries):
            return self.entries[seq_no - 1]
        return None

    def find_entry_by_id(self, uid: int):
        for entry in self.entries:
            if entry["id"] == uid:
                return entry
        return None

    #### Variant ##############################################################
    def add_entry_vnt(self, entry_seq_no: int,flags_used: int = 0,flags_prod: int = 0,offset: int = 0):
        entry = self.get_entry(entry_seq_no)
        if not entry:
            raise ValueError(f"Entry seq_no={entry_seq_no} 不存在")

        vnt = {
            "vnt_seq_no": len(entry["string_vnts"]) + 1,
            "vnt_flags_used": flags_used,
            "vnt_flags_prod": flags_prod,
            "vnt_offset": offset,
            "vnt_status": {
                "lock": False,
                "no_audit": False,
                "dollar": 0,
                "hash": 0,
                "hash_slash": 0,
            },
            "vnt_string": "",
        }

        entry["string_vnts"].append(vnt)
        return vnt

    #### C-string decode (VARIANT) ################################
    def add_vnt_string(self, vnt: dict, blob: bytes):
        start = vnt["vnt_offset"]
        end = blob.find(b"\x00", start)

        if end == -1:
            raise ValueError(f"invalid vnt c-string at offset {start}")

        vnt["vnt_string"] = blob[start:end].decode("utf-8")
        return vnt["vnt_string"]

    #### Variant access ###########################################
    def get_entry_vnts(self, entry_seq_no: int):
        entry = self.get_entry(entry_seq_no)
        if not entry:
            return []
        return entry["string_vnts"]

    def get_vnt_string(self, entry_seq_no: int, vnt_seq_no: int):
        entry = self.get_entry(entry_seq_no)
        if not entry:
            return None

        vnts = entry["string_vnts"]
        if 1 <= vnt_seq_no <= len(vnts):
            return vnts[vnt_seq_no - 1]
        return None

    def reset(self):
        self.__init__()

str_map= StringMap()


#####################################################################
# 資料結構: src_sampo 的 token 與 string/vnt_string
class DebugTokens:
    def __init__(self):
        self.creation_time: str = ""
        self.entries: list[dict] = []

    # --- Entry -------------------------------------------------
    def add_entry(self, seq_no: int, string: str, tokens: dict):
        entry = {
            "seq_no": seq_no,
            "string": string,
            "tokens": tokens,
            "string_vnts": []
        }
        self.entries.append(entry)
        return entry

    # --- Variant -----------------------------------------------
    def add_vnt(self, entry: dict, vnt_seq_no: int, vnt_string: str, tokens: dict):
        vnt = {
            "vnt_seq_no": vnt_seq_no,
            "vnt_string": vnt_string,
            "tokens": tokens
        }
        entry["string_vnts"].append(vnt)
        return vnt

dbg = DebugTokens()


####################################################################
# locale file 的讀/寫/編輯處理
class LocaleFile:

    def __init__(self):
        self.header = b""  # 4 bytes raw
        self.name1 = ""
        self.name2 = ""
        self.region = ""
        self.directory = ""
        self.flags_raw = b""

    ### 修改名稱用 ###########################
    def set_name(self, value: str):
        self.name1 = value
        self.name2 = value

    def set_region(self, value: str):
        self.region = value

    def set_directory(self, value: str):
        self.directory = value

    ### 字串編碼/解碼 (CHAR COUNT, UTF-8 storage) #######################
    @staticmethod
    def _encode_str(s: str):
        length = len(s)
        return length, s.encode("utf-8")

    @staticmethod
    def _decode_str(data: bytes, offset: int):
        length = int.from_bytes(data[offset:offset+2], "little")
        offset += 2
        raw = data[offset:offset+length]
        offset += length
        return raw.decode("utf-8"), offset

    ### 讀檔解析 #########################################################
    @classmethod
    def from_bytes(cls, data: bytes):
        obj = cls()
        offset = 0

        obj.header = data[offset:offset+4]
        offset += 4
        obj.name1, offset = obj._decode_str(data, offset)
        obj.name2, offset = obj._decode_str(data, offset)
        obj.region, offset = obj._decode_str(data, offset)
        obj.directory, offset = obj._decode_str(data, offset)
        obj.flags_raw = data[offset:]
        return obj

    ### 寫檔 ########################################################
    def to_bytes(self) -> bytes:
        out_buff = bytearray()
        out_buff += self.header

        l, b = self._encode_str(self.name1)
        out_buff += l.to_bytes(2, "little") + b
        l, b = self._encode_str(self.name2)
        out_buff += l.to_bytes(2, "little") + b
        l, b = self._encode_str(self.region)
        out_buff += l.to_bytes(2, "little") + b
        l, b = self._encode_str(self.directory)
        out_buff += l.to_bytes(2, "little") + b
        out_buff += self.flags_raw
        return bytes(out_buff)

    ### 讀取 locale file ##########################################
    def load_from_file(self, path: str):
        with open(path, "rb") as f:
            data = f.read()

        obj = self.from_bytes(data)
        self.__dict__.update(obj.__dict__)
        return self

    ### 寫入 locale file ##########################################
    def save_to_file(self, path: str):
        with open(path, "wb") as f:
            f.write(self.to_bytes())


###################################################################
# 寫入 audit tokens 記錄檔
class AuditTokenLogger:
    def __init__(self):
        self.lines = []

    def add_log(self, *log_lines: str):
        for line in log_lines:
            safe_line = str(line)

            safe_line = safe_line.replace("\\", "\\\\")        # 將控制字元轉為可視文字
            safe_line = safe_line.replace("\n", r"\n")
            safe_line = safe_line.replace("\t", r"\t")
            self.lines.append(safe_line)

        self.lines.append("-" * 100)

    def save(self):
        file_path = os.path.normpath(os.path.join( glb_vars.dst_lang_path, f"{glb_vars.dst_lang}.dbg-audit_tokens.log"))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")

        self.lines.clear()

audit = AuditTokenLogger()


####################################################################
# dbg-JSON 不配: 過濾 #tag# 和 #/tag# 的不配清單
def _filter_unpaired(tokens: dict):
    hash_items = tokens.get("hash", {}).get("items", [])
    slash_items = tokens.get("hash_slash", {}).get("items", [])

    open_map = {i["parser"][1:-1]: i["count"] for i in hash_items}
    close_map = {i["parser"][2:-1]: i["count"] for i in slash_items}

    bad_open = {}
    bad_close = {}

    for tag, cnt in open_map.items():
        if cnt != close_map.get(tag, 0):
            bad_open[f"#{tag}#"] = cnt

    for tag, cnt in close_map.items():
        if cnt != open_map.get(tag, 0):
            bad_close[f"#/{tag}#"] = cnt

    result = {}
    if bad_open:
        result["hash"] = bad_open
    if bad_close:
        result["hash_slash"] = bad_close

    return result if result else None


##########################################################################
# dbg-JSON 不配: 將 #tag#, #/tag# 不配清單匯出 debug-src_unpaired_tags.json
def export_unpaired_tags():
    json_file = f"{glb_vars.dst_lang}.dbg-src_unpaired_tags.json"
    out_path = os.path.join(glb_vars.dst_lang_path, json_file)

    def _inline_dict(d: dict) -> str:
        return "{ " + ", ".join(f"\"{k}\":{vol}" for k, vol in d.items()) + " }"

    results = []
    for e in dbg.entries:
        entry_out = {
            "seq_no": e["seq_no"],
            "string": e.get("string", "")
        }

        filtered = _filter_unpaired(e.get("tokens", {}))
        if filtered:
            entry_out.update(filtered)

        vnt_list = []
        for v in e.get("string_vnts", []):
            v_filtered = _filter_unpaired(v.get("tokens", {}))

            if v_filtered:
                vnt_obj = {
                    "vnt_seq_no": v["vnt_seq_no"],
                    "vnt_string": v.get("vnt_string", "")
                }
                vnt_obj.update(v_filtered)
                vnt_list.append(vnt_obj)

        if vnt_list:
            entry_out["string_vnts"] = vnt_list

        if len(entry_out) > 2 or "string_vnts" in entry_out:
            results.append(entry_out)

    data = {
        "_comment": out.msg("rem_json_mismatch"),
        "creation_time": glb_vars.creation_time,
        "total": len(results),
        "entries": results
    }

    raw = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        separators=(",", ":")
    )

    raw = re.sub(
        r'"hash":(\{[^}]+})',
        lambda m: '"hash":' + _inline_dict(ast.literal_eval(m.group(1))),
        raw
    )

    raw = re.sub(
        r'"hash_slash":(\{[^}]+})',
        lambda m: '"hash_slash":' + _inline_dict(ast.literal_eval(m.group(1))),
        raw
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(raw)

    print(out.msg("B_out_dbg3", dbg_mismatch=json_file))


###################################################################################
# dbg-JSON 鎖定: 將 $var$, #tag# 清單寫成 debug-locked_tokens.json
def export_locked_tokens(token_names: set[str]):
    json_file = f"{glb_vars.dst_lang}.dbg-locked_tokens.json"
    out_path = os.path.join(glb_vars.dst_lang_path, json_file)

    data = {
        "_comment": out.msg("rem_json_lock"),
        "creation_time": glb_vars.creation_time,
        "total": len(token_names),
        "tokens": sorted(token_names)
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
            separators=(",", ":")
        )

    print(out.msg("B_out_dbg2", dbg_lock=json_file))


#######################################################################
# Token-2: 抓 $var$, #tag# 清單, 自動更改 lock 值
def init_locked_export_tokens():
    token_names = set()

    for e in dbg.entries:                                                  # 收集 token names (tag / var)
        t = e.get("tokens", {})

        for item in t.get("dollar", {}).get("items", []):
            token_names.add(item["parser"][1:-1])

        for item in t.get("hash", {}).get("items", []):
            token_names.add(item["parser"][1:-1])

        for v in e.get("string_vnts", []):
            t = v.get("tokens", {})

            for item in t.get("dollar", {}).get("items", []):
                token_names.add(item["parser"][1:-1])

            for item in t.get("hash", {}).get("items", []):
                token_names.add(item["parser"][1:-1])

    for e in str_map.entries:                                              # 比對 string, 相同就 locked (True)
        if e["string"] in token_names:
            e["status"]["lock"] = True

        for v in e["string_vnts"]:
            if v["vnt_string"] in token_names:
                v["vnt_status"]["lock"] = True

    export_locked_tokens(token_names)                                      # 匯出 debug-locked_tokens.json
    export_unpaired_tags()                                                 # 匯出 debug-src_unpaired_tags.json


########################################################################
# Token-1: 解析 string 裡的 $, #, #/ 變數-標籤 數量
def analyze_tokens(s: str):
    def _to_items(cnt: Counter):
        return [
            {"parser": k, "count": cnt[k]}
            for k in sorted(cnt.keys())
        ]

    def _valid_tag(name: str) -> bool:                   # 只允許最多 1 個空白
        return name.count(" ") <= 1

    result = {
        "dollar": {"total": 0, "items": []},
        "hash": {"total": 0, "items": []},
        "hash_slash": {"total": 0, "items": []},
    }

    ### 解析 $var$ ######################################################
    dollar_matches = re.findall(r"\$([a-zA-Z_][a-zA-Z0-9_]*)\$", s)

    if dollar_matches:
        counter = Counter(f"${m}$" for m in dollar_matches)
        result["dollar"]["total"] = sum(counter.values())
        result["dollar"]["items"] = _to_items(counter)

    ### 解析 #tag# 和 #/tag# ######################################################
    matches = re.findall(r"#(/?)([a-zA-Z_][a-zA-Z0-9_ ]*)#", s)

    hash_counter = Counter()
    hash_slash_counter = Counter()

    for slash, tag_name in matches:
        if not _valid_tag(tag_name):
            continue                                            # 超過規則直接忽略

        if slash == "":
            tag = f"#{tag_name}#"
            hash_counter[tag] += 1
        else:
            tag = f"#/{tag_name}#"
            hash_slash_counter[tag] += 1

    result["hash"] = {
        "total": sum(hash_counter.values()),
        "items": _to_items(hash_counter)
    }

    result["hash_slash"] = {
        "total": sum(hash_slash_counter.values()),
        "items": _to_items(hash_slash_counter)
    }

    return result


###############################################################################
# 讀取並解析一個 string file
def parse_one_file(filepath: str, file_key: str):

    with open(filepath, "rb") as f:
        buf = f.read()

    if buf[0:4] != b"STR\x02":
        raise ValueError(f"{filepath} header error")

    str_map.header = buf[0:4].hex()
    str_map.entries_num[file_key] = read_u16(buf, 4)
    index = 6                                                  # buf 讀檔 index

    ### 讀一筆 entries 主體 ####################################
    for _ in range(str_map.entries_num[file_key]):

        uid = read_u64(buf, index); index += 8
        var_num = read_u16(buf, index); index += 2
        flags_prod = read_u16(buf, index); index += 2
        str_offset = read_u32(buf, index); index += 4
        entry = str_map.add_entry(uid, var_num, flags_prod, str_offset)
        s = str_map.add_string(entry, buf)

        tokens = analyze_tokens(s)                                              # 解析 string 的 $, #, #/
        entry["status"]["dollar"] = tokens["dollar"]["total"]
        entry["status"]["hash"] = tokens["hash"]["total"]
        entry["status"]["hash_slash"] = tokens["hash_slash"]["total"]
        dbg_entry = dbg.add_entry(entry["seq_no"], s, tokens)                   # 結果回存 class dbg

        ### 讀取一筆 entry 的所有變體 ###########################
        vnt_count = var_num - 1
        for _ in range(vnt_count):
            flags_used = read_u64(buf, index); index += 8
            vnt_flags_prod = read_u16(buf, index); index += 2
            vnt_offset = read_u32(buf, index); index += 4

            vnt = str_map.add_entry_vnt(entry["seq_no"], flags_used, vnt_flags_prod, vnt_offset)
            vs = str_map.add_vnt_string(vnt, buf)

            tokens = analyze_tokens(vs)                                         # 解析 vnt_string 的 $, #, #/
            vnt["vnt_status"]["dollar"] = tokens["dollar"]["total"]
            vnt["vnt_status"]["hash"] = tokens["hash"]["total"]
            vnt["vnt_status"]["hash_slash"] = tokens["hash_slash"]["total"]
            dbg.add_vnt(dbg_entry, vnt["vnt_seq_no"], vs, tokens)               # 結果回存 class dbg


####################################################################
# dbg-JSON: 匯出 debug 用 debug-src_sample.json
def export_debug_json():
    json_file = f"{glb_vars.dst_lang}.SrcSampTok.json"
    out_path = os.path.join(glb_vars.dst_lang_path, json_file)

    data = dbg.__dict__
    out_data = {
        "_comment": out.msg("rem_json_sample"),
        **data
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump( out_data, f, indent=2, ensure_ascii=False, separators=(",", ":") )

    print(out.msg("B_out_dbg1", dbg_samp=json_file))


####################################################################
# Main-JSON: 將 ststus { dollar,hash, hash_slash } 轉化成一列字串.
def encode_status(d: dict) -> str:
    def norm(v):
        if isinstance(v, bool):
            return "1" if v else "0"
        return str(v)

    return ", ".join(f"{k}={norm(v)}" for k, v in d.items())


####################################################################
# Main-JSON: 將 Class StringMap 匯出 StringMap.json 和 MainTable.json 兩檔
def export_main_jsons():
    # ---------- StringMap.json ----------
    sm = {
        "creation_time": str_map.creation_time,
        "entries": []
    }

    for e in str_map.entries:
        obj = {
            "seq_no": e["seq_no"],
            "status": encode_status(e["status"]),
            "string": e["string"],
        }

        if e["string_vnts"]:
            obj["string_vnts"] = [
                {
                    "vnt_seq_no": v["vnt_seq_no"],
                    "vnt_status": encode_status(v["vnt_status"]),
                    "vnt_string": v["vnt_string"],
                }
                for v in e["string_vnts"]
            ]

        sm["entries"].append(obj)

    string_json = f"{glb_vars.dst_lang}.StringMap.json"
    with open(os.path.join(glb_vars.dst_lang_path, string_json), "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=2, ensure_ascii=False, separators=(",", ":"))

    # ---------- MainTable.json ----------
    header_str = bytes.fromhex(str_map.header).decode("latin-1")

    mt = {
        "creation_time": str_map.creation_time,
        "original_language": str_map.original_language,
        "file_version": str_map.file_version,
        "header": header_str,
        "entries_num": str_map.entries_num,
        "entries": []
    }

    for e in str_map.entries:
        obj = {
            "seq_no": e["seq_no"],
            "uid": e["id"],
            "var_num": e["var_num"],
            "flags_prod": e["flags_prod"],
            "offset": e["offset"],
        }

        if e["string_vnts"]:
            obj["string_vnts"] = [
                {
                    "vnt_seq_no": v["vnt_seq_no"],
                    "vnt_flags_used": v["vnt_flags_used"],
                    "vnt_flags_prod": v["vnt_flags_prod"],
                    "vnt_offset": v["vnt_offset"],
                }
                for v in e["string_vnts"]
            ]

        mt["entries"].append(obj)

    main_json = f"{glb_vars.dst_lang}.MainMap.json"
    with open(os.path.join(glb_vars.dst_lang_path, main_json), "w", encoding="utf-8") as f:
        json.dump(mt, f, indent=2, ensure_ascii=False, separators=(",", ":"))

    print(out.msg("B_out_main", main_table=main_json))
    print(out.msg("B_out_txt", string_txt=string_json))
    str_map.reset()


###################################################################
# func2: 讀取 4 個 string file 至 str_map
def read_string_file():

    str_map.file_version = glb_vars.game_ver                                                        # 記錄 遊戲檔案版本
    dbg.creation_time = str_map.creation_time = glb_vars.creation_time = datetime_string(0)         # 同步記錄 3 大 Class DB 的 creation_time 初值
    src_lang = str_map.original_language = glb_vars.orig_lang = glb_vars.src_lang                   # 同步記錄 2 大 Class DB 的[樣本語言]
    src_lang_path = glb_vars.src_lang_path
    files = {
        "3": f"{src_lang}_3FFFFFFFFFFFFFFF.string",
        "7": f"{src_lang}_7FFFFFFFFFFFFFFF.string",
        "B": f"{src_lang}_BFFFFFFFFFFFFFFF.string",
        "F": f"{src_lang}_FFFFFFFFFFFFFFFF.string",
    }

    for key, fname in files.items():                                        # 依序抓 string_file 解讀/儲放
        path = os.path.join(src_lang_path, fname)
        parse_one_file(path, key)

    print(out.msg("B_export", dst=glb_vars.dst_lang_path ))
    export_debug_json()                                                     # 匯出 debug-src_sample.json
    init_locked_export_tokens()                                             # 設定 ststus.lock 初值, 並匯出 debug-locked_tokens.json, debug-src_unpaired_tags.json
    export_main_jsons()                                                     # 匯出 StringMap.json / MainTable.json


#####################################################################################################################
# Func3: load_main_map()
def load_main_map():

    json_file = f"{glb_vars.dst_lang}.MainMap.json"
    path = os.path.join(glb_vars.dst_lang_path, json_file)
    data = load_json(path)
    if data is None:
        return False

    str_map.creation_time = data["creation_time"]
    str_map.original_language = data["original_language"]
    str_map.file_version = data["file_version"]
    str_map.header = data["header"].encode("latin-1")

    str_map.entries_num = data["entries_num"]
    str_map.entries.clear()
    for e in data["entries"]:
        entry = str_map.add_entry(
            uid=e["uid"],
            var_num=e["var_num"],
            flags_prod=e["flags_prod"],
            offset=e["offset"],
        )

        for v in e.get("string_vnts", []):
            str_map.add_entry_vnt(
                entry_seq_no=entry["seq_no"],
                flags_used=v["vnt_flags_used"],
                flags_prod=v["vnt_flags_prod"],
                offset=v["vnt_offset"],
            )

    print(out.msg("C_json_chk2", jsonfile=json_file, creat_time=str_map.creation_time))
    return True


#############################################################
# Func3: status parser // 回傳: 解碼過的 status, err_msg
def decode_status(s: str):
    bool_fields = {"lock", "no_audit"}
    result = {}

    for part in s.split(","):
        if "=" not in part:
            return None, out.msg("C_stat_err1", part=part)

        k, v = part.strip().split("=", 1)

        try:
            value = int(v)
        except ValueError:
            return None, out.msg("C_stat_err2", key=k, val=v)

        if k in bool_fields and value not in (0, 1):
            return None, out.msg("C_stat_err2", key=k, val=value)

        result[k] = value

    return result, None


################################################################
# Func3: load StringMap.json, 回傳值: 建檔同步(True/False), Json檔正常(True/False)
def load_string_json():

    json_file = f"{glb_vars.dst_lang}.StringMap.json"
    path = os.path.join(glb_vars.dst_lang_path, json_file)
    data = load_json(path)
    if data is None:
        return False, False

    glb_vars.creation_time = data["creation_time"]                              # MainMap.json 和 SrcSampTok.json 都有全域變數可存建立時間, StringMap.json 沒有, 就借用 glb_vars
    for e in data["entries"]:
        entry = str_map.get_entry(e["seq_no"])
        if not entry:
            continue

        entry["string"] = e["string"]
        st, err = decode_status(e["status"])
        if err:
            seq_no = e.get("seq_no")
            print(f"!!! seq_no={seq_no}, {err}")
            return False, False

        entry["status"]["lock"] = st.get("lock", 0)
        entry["status"]["no_audit"] = st.get("no_audit", 0)

        vnts_json = e.get("string_vnts", [])
        vnts = entry["string_vnts"]
        for vj, v in zip(vnts_json, vnts):
            v["vnt_string"] = vj["vnt_string"]

            vst, err = decode_status(vj["vnt_status"])
            if err:
                vnt_seq_no = vj.get("vnt_seq_no")
                print(f"!!! seq_no={e["seq_no"]}, vnt_seq_no={vnt_seq_no}, {err}")
                return False, False

            v["vnt_status"]["lock"] = vst.get("lock", 0)
            v["vnt_status"]["no_audit"] = vst.get("no_audit", 0)

    print(out.msg("C_json_chk2", jsonfile=json_file, creat_time=glb_vars.creation_time))
    if str_map.creation_time == glb_vars.creation_time:      # 比對建檔時間是否一致
        return True, True
    else:
        return False, True


#######################################################################################
# Func3: load SrcSampTok.json     回傳值: 建檔同步(True/False), Json檔正常(True/False)
def load_srcsamp_json():

    json_file = f"{glb_vars.dst_lang}.SrcSampTok.json"
    path = os.path.join(glb_vars.dst_lang_path, json_file)
    data = load_json(path)
    if data is None:
        return False, False

    dbg.creation_time = data["creation_time"]
    dbg.entries.clear()
    for e in data["entries"]:
        entry = str_map.get_entry(e["seq_no"])
        tokens = e["tokens"]

        dbg_entry = dbg.add_entry(
            seq_no=e["seq_no"],
            string=e["string"],
            tokens=e["tokens"],
        )

        st = entry["status"]
        st["dollar"] = tokens["dollar"]["total"]
        st["hash"] = tokens["hash"]["total"]
        st["hash_slash"] = tokens["hash_slash"]["total"]

        json_vnts = e.get("string_vnts", [])
        entry_vnts = entry["string_vnts"]
        for vj, vnt in zip(json_vnts, entry_vnts):
            vt = vj["tokens"]

            dbg.add_vnt(
                entry=dbg_entry,
                vnt_seq_no=vj["vnt_seq_no"],
                vnt_string=vj["vnt_string"],
                tokens=vt,
            )

            vst = vnt["vnt_status"]
            vst["dollar"] = vt["dollar"]["total"]
            vst["hash"] = vt["hash"]["total"]
            vst["hash_slash"] = vt["hash_slash"]["total"]

    print(out.msg("C_json_chk2", jsonfile=json_file, creat_time=dbg.creation_time))
    if str_map.creation_time == dbg.creation_time:      # 比對建檔時間是否一致
        return True, True
    else:
        return False, True


####################################################################
# Func3: 讀入三 Json 並補完 str_map, 待命重建 string_files
def merge_json_data():

    print(out.msg("C_json_chk1"))
    json_ok1 = load_main_map()
    time_sync1, json_ok2 = load_string_json()
    time_sync2, json_ok3 = load_srcsamp_json()

    if not all([json_ok1, json_ok2, json_ok3]):                                                    # 只要有 JSON 內容故障, 就跳回主選單
        pause(out.msg("hit_next"))
        return False

    if not time_sync1 or not time_sync2:                                                           # 若Json 三檔的建檔時間不同 -> 不是同一組檔案
        submit2 = input_one_letter(out.msg("C_json_chk4"), "YyNn")
        if submit2 in ("n", "N"):
            return False

    if glb_vars.game_ver != str_map.file_version:                                                  # 檢查版本: json 遊戲版本不符, 直接跳回主選單
        print(out.msg("C_json_chk3", json_ver=str_map.file_version, game_ver=glb_vars.game_ver))
        pause(out.msg("hit_next"))
        return False

    return True


##########################################################
# 比對 string 的 tokens 數與原始值, 記錄錯誤, 偵錯用
def audit_string_token(str_e, dbg_e, parent_seq_no=None):
    is_vnt = "vnt_seq_no" in str_e
    status_key = "vnt_status" if is_vnt else "status"
    string_key = "vnt_string" if is_vnt else "string"

    str_status = str_e.get(status_key, {})
    current_string = str_e.get(string_key, "")
    dbg_string = dbg_e.get(string_key, dbg_e.get("string", ""))

    dbg_tokens = dbg_e.get("tokens", {})
    if str_status.get("lock", False):                               # 標示已鎖定者, 取原始值
        return dbg_string

    if str_status.get("no_audit", False):                           # 標示不檢查者, 不檢查
        return current_string

    str_tokens = analyze_tokens(current_string)                     # 解析記算 tokens 數
    diff_parts = []
    for parser_type in ("dollar", "hash", "hash_slash"):
        str_block = str_tokens.get(parser_type, {})
        dbg_block = dbg_tokens.get(parser_type, {})

        str_items = {
            item["parser"]: item["count"]
            for item in str_block.get("items", [])
        }

        dbg_items = {
            item["parser"]: item["count"]
            for item in dbg_block.get("items", [])
        }

        all_parsers = sorted(set(str_items) | set(dbg_items))
        for parser in all_parsers:
            s_count = str_items.get(parser, 0)
            d_count = dbg_items.get(parser, 0)

            if s_count != d_count:
                diff_parts.append(
                    f"{parser}: {s_count}/{d_count}"
                )

    if diff_parts:
        seq_no = (
            str_e.get("seq_no")
            or dbg_e.get("seq_no")
            or parent_seq_no
            or -1
        )

        seq_line = f"{out.msg("seq")}\"seq_no\":{seq_no}"
        if is_vnt:
            vnt_seq_no = str_e.get(
                "vnt_seq_no",
                dbg_e.get("vnt_seq_no", -1)
            )
            seq_line += f", \"vnt_seq_no\":{vnt_seq_no}"

        audit.add_log(
            seq_line,
            f"{out.msg("orig_str")}{dbg_string}",
            f"{out.msg("dst_str")}{current_string}",
            f"{out.msg("miss_token")}{', '.join(diff_parts)}"
        )

    return current_string


###########################################################
# Func3: 寫入一個 String_Map 檔
def _write_one_string_file(entries, out_path: str):

    entry_count = len(entries)
    table_size = 0                                                 # ---------- 第一輪：計算 table size ----------
    for e in entries:
        vnt_count = max(0, e["var_num"] - 1)
        table_size += 16 + (14 * vnt_count)

    base_offset = 4 + 2 + table_size                               # string blob 起始位置

    table = bytearray()                                            # ---------- 第二輪：同步建立 table + blob ----------
    blob = bytearray()
    for e in entries:
        dbg_entry = dbg.entries[e["seq_no"] - 1]
        base_string = audit_string_token(e, dbg_entry)             # 回傳 string, 檢測字串 tokens 數, 並記錄異常
        base_offset_cur = base_offset + len(blob)
        blob.extend(base_string.encode("utf-8") + b"\x00")

        table.extend(write_u64(e["id"]))                           # --- entry header ---
        table.extend(write_u16(e["var_num"]))
        table.extend(write_u16(e["flags_prod"]))
        table.extend(write_u32(base_offset_cur))

        dbg_vnts = dbg_entry.get("string_vnts", [])
        for idx, v in enumerate(e.get("string_vnts", [])):
            dbg_vnts = dbg_entry.get("string_vnts", [])
            dbg_vnt = dbg_vnts[idx] if idx < len(dbg_vnts) else {}

            vnt_string = audit_string_token( v, dbg_vnt, parent_seq_no=e["seq_no"])      # 回傳 string, 檢測字串 tokens 數, 並記錄異常
            vnt_offset_cur = base_offset + len(blob)
            blob.extend(vnt_string.encode("utf-8") + b"\x00")
            table.extend(write_u64(v["vnt_flags_used"]))
            table.extend(write_u16(v["vnt_flags_prod"]))
            table.extend(write_u32(vnt_offset_cur))

    output = bytearray()                                                                 # ---------- 組合完整檔案 ----------
    output.extend(b"STR\x02")
    output.extend(write_u16(entry_count))
    output.extend(table)
    output.extend(blob)

    print(out.msg("C_export2", out=out_path))
    with open(out_path, "wb") as f:                                                      # ---------- 覆寫輸出 ----------
        f.write(output)


###############################################################
# Func3: 準備回寫 string 檔案
def write_string_files():
    base_path = glb_vars.dst_lang_path
    lang = glb_vars.dst_lang

    files = {
        "3": f"{lang}_3FFFFFFFFFFFFFFF.string",
        "7": f"{lang}_7FFFFFFFFFFFFFFF.string",
        "B": f"{lang}_BFFFFFFFFFFFFFFF.string",
        "F": f"{lang}_FFFFFFFFFFFFFFFF.string",
    }

    order = ["3", "7", "B", "F"]
    idx = 0

    audit.add_log(out.msg("rem_audit_log"))                                    # 開啟: token不符記錄檔
    print(out.msg("C_export1"))
    for k in order:
        count = str_map.entries_num[k]
        subset = str_map.entries[idx: idx + count]
        idx += count

        out_path = os.path.normpath(os.path.join(base_path, files[k]))         # os.path.normpath() 將路徑的 / 和 \ 一致化
        _write_one_string_file(subset, out_path)

    audit.save()                                                               # 存檔: token不符記錄檔
    print(out.msg("C_export3", dst_lang=glb_vars.dst_lang))


################################################################
# Func 4: 舊版 String_Texts.json 轉新版 StringMap.json
def  migrate_legacy_json():

    date = datetime_string(7)
    base = glb_vars.dst_lang_path
    lang = glb_vars.dst_lang
    new_path = os.path.normpath( os.path.join(base, f"{lang}.StringMap.json") )
    old_path = os.path.normpath( os.path.join(base, f"{lang}_String_Texts.json") )
    backup_path = os.path.join(base, f"{lang}.StringMap.{date}.json")

    if not os.path.exists(new_path):                            # 檢查 StringMap.json 是否存在
        print(out.msg("D_src_err", file=new_path))
        return False

    if not os.path.exists(old_path):                            # 檢查 _String_Texts.json 是否存在
        print(out.msg("D_src_err", file=old_path))
        return False

    with open(new_path, "r", encoding="utf-8") as f:            # 讀檔
        new_data = json.load(f)

    with open(old_path, "r", encoding="utf-8") as f:
        old_data = json.load(f).get("texts", [])

    expected = 0
    for e in new_data.get("entries", []):
        if e.get("seq_no") == 1:
            continue

        expected += 1                                                       # base string
        expected += len(e.get("string_vnts", []))                           # variants

    if expected != len(old_data):
        print(out.msg("D_diff_err", new=expected, old=len(old_data)))
        return False

    os.rename(new_path, backup_path)                                        # 備份 StringMap.json
    cursor = 0
    result = {
        "creation_time": new_data.get("creation_time", ""),
        "entries": []
    }

    for e in new_data.get("entries", []):
        if e.get("seq_no") == 1:
            result["entries"].append(e)
            continue

        if cursor >= len(old_data):
            print(out.msg("D_eof_err", s_no=e.get('seq_no'), v_no=0))
            return False

        e["string"] = old_data[cursor]["Text"]
        cursor += 1

        for v in e.get("string_vnts", []):
            if cursor >= len(old_data):
                print(out.msg("D_eof_err", s_no=e.get('seq_no'), v_no=v.get('vnt_seq_no')))
                return False

            v["vnt_string"] = old_data[cursor]["Text"]
            cursor += 1

        result["entries"].append(e)

    if cursor != len(old_data):
        err = (
            f"merge incomplete: "
            f"used={cursor}, total={len(old_data)}"
        )
        print(f"[ERROR] {err}")
        return False

    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
            separators=(",", ":")
        )

    print(out.msg("D_export1"))
    print(out.msg("C_export2", out=new_path))
    return True


####################################################################
# # UI-D (func4):
def migrate_legacy_json_ui():

    while True:
        clear_screen()
        print(out.msg("D_title"))
        select = input_one_letter(out.msg("D_dst"), "123456789")
        dst_lang = select_to_lang_set(select, "dst")

        print(out.msg("D_submit1", dst_lang=dst_lang))
        print(out.msg("D_submit2", dst_path=glb_vars.dst_lang_path,
                                   old_json=f"{dst_lang}_String_Texts.json",
                                   new_json=f"{dst_lang}.StringMap.json"))
        print(out.msg("D_submit3", dst_lang=dst_lang))
        submit = input_one_letter(out.msg("ok?"), "YyNnBbQq")

        if submit in ("n", "N"):                                                        # NO, 重新選擇[樣本/轉出]語言
            pass
        elif submit in ("q", "Q", "b", "B"):                                            # QUIT/BACK, 回到主選單流程
            return submit
        else:                                                                           # YES, 進行功能

            migrate_legacy_json()
            pause(out.msg("hit_next"))
            return "B"


####################################################################
# UI-C (func3): JSON 生成字串檔
def json_rebuild_strings():

    while True:
        clear_screen()
        print(out.msg("C_title"))
        select = input_one_letter(out.msg("C_dst"), "123456789")
        dst_lang = select_to_lang_set(select, "dst")

        print(out.msg("C_submit1", dst_lang=dst_lang))
        print(out.msg("C_submit2", dst_path=glb_vars.dst_lang_path,
                                   main_json=f"{dst_lang}.MainMap.json",
                                   string_json=f"{dst_lang}.StringMap.json",
                                   samp_json=f"{dst_lang}.SrcSampTok.json"))
        submit = input_one_letter(out.msg("ok?"), "YyNnBbQq")

        if submit in ("n", "N"):                                                        # NO, 重新選擇[樣本/轉出]語言
            pass
        elif submit in ("q", "Q", "b", "B"):                                            # QUIT/BACK, 回到主選單流程
            return submit
        else:                                                                           # YES, 進行功能
            ok = merge_json_data()                                                      # 讀取三 json 並合併欄位資料
            if not ok:
                break

            write_string_files()
            pause(out.msg("hit_next"))
            return "B"


####################################################################
# UI-B (func2): 字串檔轉換為 JSON 文字檔
def strings_conv_json():

    while True:
        clear_screen()
        print(out.msg("B_title"))
        select = input_one_letter(out.msg("B_src"), "123456789")
        src_lang = select_to_lang_set(select, "src")
        select = input_one_letter(out.msg("B_dst"), "123456789")
        dst_lang = select_to_lang_set(select, "dst")

        print(out.msg("B_submit1", src=src_lang, dst=dst_lang))
        submit = input_one_letter(out.msg("ok?"), "YyNnBbQq")

        if submit in ("n", "N"):                                                        # NO, 重新選擇[樣本/轉出]語言
            pass
        elif submit in ("q", "Q", "b", "B"):                                            # QUIT/BACK, 回到主選單流程
            return submit
        else:                                                                           # YES, 進行功能
            ok, _ = check_lang_pack(src_lang, "dir", need_bak=False)              # = 樣本檔是否存在 (補測 中日韓)
            if ok:
                _, err_log = check_lang_pack(dst_lang, "dir", need_bak=True)      # - 重點: 有舊 lang_dir 存在, 就要備份
                if err_log is not None:                                                 # - 備份失敗 (有 err_log)
                    print(out.msg("B_dst_err", err=err_log))                            # - 目的異常或備份失敗之錯誤顯示
                else:

                    if src_lang == dst_lang:                                            # - !! 特例處理: 當 src==dst 時, 會因備份喪失 src_path, 以此修正
                        glb_vars.src_lang_path = glb_vars.dir_bak_path

                    os.makedirs(glb_vars.dst_lang_path, exist_ok=True)                  # - 備份後, 建立新 lang_dir
                    read_string_file()
            else:
                print(out.msg("B_src_err"))                                             # = 樣本檔不存在

            pause(out.msg("hit_next"))
            return "B"


#####################################################################
# UI-A (func1): 克隆產生新語言包, 含 .locale 檔
def clone_language_pack():

    loc = LocaleFile()                                                                           # 建立 locale class
    while True:
        clear_screen()
        print(out.msg("A_title"))
        select = input_one_letter(out.msg("A_src"), "123456")
        src_lang = select_to_lang_set(select, "src")
        select = input_one_letter(out.msg("A_dst"), "789")
        dst_lang = select_to_lang_set(select, "dst")

        max_num, name = limited_input_bytes(out.msg("A_lang_name"), 16)                # 限制輸入 16 字元
        print(out.msg("A_submit1", src=src_lang, dst=dst_lang, name=name))
        submit = input_one_letter(out.msg("ok?"), "YyNnBbQq")

        if submit in ("n", "N"):  # NO, 重新選擇[樣本/轉出]語言
            pass
        elif submit in ("q", "Q", "b", "B"):  # QUIT/BACK, 回到主選單流程
            return submit
        else:  # YES, 進行功能
            src_locale = f"{glb_vars.src_lang_path}.locale"                                       # 完整的[樣本.locale]路徑
            loc.load_from_file(src_locale)                                                        # 讀取樣本 locale 檔
            if loc.header == b'LOC\x02':                                                          # 用檔頭判斷 locale 是否正確

                _, err_log = check_lang_pack(dst_lang, "both", need_bak=True)               # 是否有[新語言包]已存在, 若是備份
                if err_log is not None:                                                           # - 備份失敗 (有 err_log)
                    print(out.msg("A_dst_err", err=err_log))                                      #   目的異常或備份失敗之錯誤顯示
                else:                                                                             # - 備份成功
                    print(out.msg("A_export"))
                    _, err_log = clone_string_map()                                               #   克隆 StringMap
                    if err_log is not None:                                                       # ... 克隆失敗 (有 err_log)
                        print(out.msg("A_clone_err", err=err_log))
                    else:                                                                         # ... 克隆完成, 設定 .locale
                        loc.set_name(name)
                        loc.set_directory(dst_lang)
                        dst_locale = f"{glb_vars.dst_lang_path}.locale"
                        loc.save_to_file(dst_locale)
                        print(f"  - {dst_locale}")
                        print(out.msg("A_end", src_lang=src_lang))
            else:
                print(out.msg("A_src_err", src_locale=src_locale))                                # 樣本檔不存在或檔頭不正確

            pause(out.msg("hit_next"))
            return "B"


####################################################################
# UI: 繪製主選單
def menu():

    # clear_screen()
    print(out.msg("menu_1",date="2026.05.08"))
    print(out.msg("menu_2"))
    print(out.msg("menu_3"))
    print(out.msg("menu_4"))
    print(out.msg("menu_5"))
    print(out.msg("menu_6"))

    choice0 = input_one_letter(out.msg("menu_7"), "123456")             # menu_7, "\n\t請選擇功能(1~6): "
    return choice0


####################################################################
# 主程式
def main():

    actions = {
        "1": clone_language_pack,                 # 克隆一組語言包
        "2": strings_conv_json,                   # 字串檔轉換為 JSON 文字檔
        "3": json_rebuild_strings,                # JSON 重建字串檔
        "4": migrate_legacy_json_ui,                 # 舊版 JSON 轉換新板本
    }

    ready = init_and_check()                      # 工作路徑檢查與設定路徑, 回傳 True/False
    if not ready:                                 # 工作路徑錯誤, 結束
        return

    while True:
        select = menu()                           # 主功能選單
        func = actions.get(select)

        if func:
            select = func()

        if select in ("5", "Q", "q"):             # 結束離開
            break

        clear_screen()                            # 清除螢幕


################################################
#  判斷是否為入口執行, 並指定主程式
if __name__ == "__main__":
    main()