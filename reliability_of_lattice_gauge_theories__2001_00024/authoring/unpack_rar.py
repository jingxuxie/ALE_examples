import ctypes
import ctypes.util
import pathlib
import sys


def extract(source, destination):
    library = ctypes.CDLL(ctypes.util.find_library("archive"))
    library.archive_read_new.restype = ctypes.c_void_p
    signatures = {
        "archive_read_support_filter_all": [ctypes.c_void_p],
        "archive_read_support_format_all": [ctypes.c_void_p],
        "archive_read_open_filename": [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t],
        "archive_read_next_header": [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)],
        "archive_read_data": [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t],
        "archive_read_free": [ctypes.c_void_p],
        "archive_entry_pathname": [ctypes.c_void_p],
        "archive_entry_filetype": [ctypes.c_void_p],
        "archive_error_string": [ctypes.c_void_p],
    }
    for name, arguments in signatures.items():
        getattr(library, name).argtypes = arguments
    library.archive_entry_pathname.restype = ctypes.c_char_p
    library.archive_error_string.restype = ctypes.c_char_p
    library.archive_read_data.restype = ctypes.c_ssize_t
    archive = library.archive_read_new()
    library.archive_read_support_filter_all(archive)
    library.archive_read_support_format_all(archive)
    if library.archive_read_open_filename(archive, str(source).encode(), 65536) != 0:
        raise RuntimeError(library.archive_error_string(archive))
    header = ctypes.c_void_p()
    buffer = ctypes.create_string_buffer(65536)
    destination = pathlib.Path(destination).resolve()
    while library.archive_read_next_header(archive, ctypes.byref(header)) == 0:
        relative = pathlib.Path(library.archive_entry_pathname(header).decode())
        target = (destination / relative).resolve()
        if destination not in target.parents:
            raise ValueError(relative)
        if library.archive_entry_filetype(header) == 16384:
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as stream:
            while True:
                count = library.archive_read_data(archive, buffer, len(buffer))
                if count < 0:
                    raise RuntimeError(library.archive_error_string(archive))
                if count == 0:
                    break
                stream.write(buffer.raw[:count])
        print(relative)
    library.archive_read_free(archive)


if __name__ == "__main__":
    extract(*sys.argv[1:])
