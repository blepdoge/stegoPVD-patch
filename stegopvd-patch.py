#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# fixed by blepdoge with <3

import argparse
import logging
import os
import re
from PIL import Image

# Setup standard logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("StegoPVD")

class PVD(object):
    def __init__(self, image_path, secret_path=None):
        self.image_path = image_path
        self.secret_path = secret_path
        self.data = ""
        try:
            self.obj = Image.open(image_path).convert('RGB')
            logger.debug(f"Image size: {self.obj.size[0]}x{self.obj.size[1]}")
        except Exception as e:
            logger.error(f"Could not open image: {e}")
            exit(1)

    @staticmethod
    def bin2str(binary_gen):
        """Converts a string of bits to a string of characters."""
        chars = []
        for i in range(0, len(binary_gen), 8):
            byte = binary_gen[i:i+8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
        return "".join(chars)

    @staticmethod
    def get_printable_strings(data, min_len=16):
        """Standard 'strings' implementation using regex."""
        # Finds sequences of printable characters
        pattern = re.compile(f'[\\x20-\\x7E]{{{min_len},}}')
        return pattern.findall(data)

    def extract(self, channels="RGB", zigzag=True):
        logger.debug(f"Extracting: Channels {channels}, Zigzag {zigzag}")
        w, h = self.obj.size
        bit_stream = ""
        
        for y in range(h):
            # Process pairs of pixels
            for x in range(1, w, 2):
                actual_x = x
                # Apply Zig-Zag Traversing Scheme
                if zigzag and (y % 2 == 1):
                    actual_x = (w - 1) - (x - 1)
                
                curr_p = self.obj.getpixel((actual_x, y))
                prev_p = self.obj.getpixel((actual_x - 1, y))
                
                pixel = {"R": curr_p[0], "G": curr_p[1], "B": curr_p[2]}
                prev_pixel = {"R": prev_p[0], "G": prev_p[1], "B": prev_p[2]}

                for c in channels:
                    d = abs(pixel[c] - prev_pixel[c])
                    
                    # PVD Range Table logic
                    if 0 <= d <= 7:
                        b, lower = 3, 0
                    elif 8 <= d <= 15:
                        b, lower = 3, 8
                    elif 16 <= d <= 31:
                        b, lower = 4, 16
                    elif 32 <= d <= 63:
                        b, lower = 5, 32
                    elif 64 <= d <= 127:
                        b, lower = 6, 64
                    elif 128 <= d <= 255:
                        b, lower = 7, 128
                    else:
                        continue
                    
                    bit_stream += bin(d - lower)[2:].zfill(b)
        
        self.data = self.bin2str(bit_stream)

    def bruteforce(self, bf_channels=False, nchars=16):
        import itertools
        
        # Define channel combinations
        if bf_channels:
            combos = []
            for r in range(1, 4):
                for combo in itertools.permutations("RGB", r):
                    combos.append("".join(combo))
        else:
            combos = ["RGB"]

        for ch in combos:
            for zz in [True, False]:
                self.extract(channels=ch, zigzag=zz)
                found = self.get_printable_strings(self.data, nchars)
                for s in found:
                    logger.info(f"[CH: {ch} | ZZ: {zz}] Found: {s}")
                    if self.secret_path:
                        self.write(content=s)

    def write(self, filename=None, content=None):
        out_file = self.secret_path or filename
        if out_file is None:
            base = os.path.basename(self.image_path)
            out_file = os.path.splitext(base)[0] + "-secret.txt"
        
        with open(out_file, 'a', encoding='utf-8') as f:
            f.write((content or self.data) + "\n")
        return self

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StegoPVD: Pixel Value Differencing Tool")
    parser.add_argument("-w", "--write", help="write data to a file")
    subparsers = parser.add_subparsers(dest="command")

    # Extract Subcommand
    ext_parser = subparsers.add_parser('extract', help="Manually extract hidden data")
    ext_parser.add_argument("image", help="Path to image")
    ext_parser.add_argument("-c", "--channels", default="RGB", help="Channels (e.g., RGB, B, RG)")
    ext_parser.add_argument("-z", "--zigzag", action="store_true", help="Apply Zig-Zag scheme")

    # Bruteforce Subcommand
    bf_parser = subparsers.add_parser('bruteforce', help="Bruteforce extraction parameters")
    bf_parser.add_argument("image", help="Path to image")
    bf_parser.add_argument("-c", "--channels", action="store_true", help="Bruteforce channel combinations")
    bf_parser.add_argument("-n", "--nchars", type=int, default=16, help="Min length for strings")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        exit()

    pvd = PVD(args.image, args.write)

    if args.command == "bruteforce":
        pvd.bruteforce(bf_channels=args.channels, nchars=args.nchars)
    elif args.command == "extract":
        pvd.extract(channels=args.channels, zigzag=args.zigzag)
        print(f"--- Raw Extracted Data ---\n{pvd.data}\n--------------------------")
        if args.write:
            pvd.write()
