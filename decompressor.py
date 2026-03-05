import struct
import zlib
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

class MC_CLE_Decompressor:
    def __init__(self):
        pass
    
    def decompress_rle(self, data):
        """RLE decompression according to the code implementation"""
        output = bytearray()
        i = 0
        data_len = len(data)
        
        while i < data_len:
            byte = data[i]
            i += 1
            
            if byte == 0xFF:  # 255
                if i >= data_len:
                    break
                count = data[i]
                i += 1
                
                if count < 3:
                    # Encoding 1-3 bytes with value 255
                    count += 1
                    output.extend([0xFF] * count)
                else:
                    # Encoding longer sequence
                    if i >= data_len:
                        break
                    count += 1
                    value = data[i]
                    i += 1
                    output.extend([value] * count)
            else:
                # Single byte
                output.append(byte)
        
        return bytes(output)
    
    def decompress_lzx_xmem(self, data):
        """
        LZX decompression compatible with XMemCompress (Xbox 360)
        Note: This is a simplified version - full decompression would require
        implementing the LZX algorithm
        """
        # In reality, we need a full LZX library
        # For now, return raw data as a placeholder
        # TODO: Full LZX implementation or use external library
        return data
    
    def decompress_zlib(self, data):
        """ZLIB decompression"""
        try:
            return zlib.decompress(data)
        except:
            # Try without zlib header
            try:
                return zlib.decompress(data, -15)
            except:
                raise ValueError("Cannot decompress ZLIB data")
    
    def decompress_ps3_zlib(self, data):
        """
        PS3 ZLIB decompression (with 4-byte big-endian header)
        """
        if len(data) < 4:
            raise ValueError("Not enough data for PS3 ZLIB")
        
        # Read size from first 4 bytes (big-endian)
        decompressed_size = struct.unpack('>I', data[:4])[0]
        compressed_data = data[4:]
        
        # Decompress without zlib header
        decompressed = zlib.decompress(compressed_data, -15)
        
        if len(decompressed) != decompressed_size:
            print(f"Warning: Decompressed size ({len(decompressed)}) differs from expected ({decompressed_size})")
        
        return decompressed
    
    def identify_compression_type(self, data):
        """
        Attempts to identify compression type based on first bytes
        """
        if len(data) < 8:
            return "UNKNOWN"
        
        # Check if it might be PS3 ZLIB (first 4 bytes are size)
        potential_size = struct.unpack('>I', data[:4])[0]
        if potential_size < 1024*1024*10:  # Reasonable size < 10MB
            return "PS3ZLIB"
        
        # Check if it's LZXRLE (characteristic patterns)
        # This is very simplified
        if data[0] == 0x00 and data[4] == 0x00:
            return "LZXRLE"
        
        return "UNKNOWN"
    
    def decompress_file(self, input_file, output_file, compression_type=None):
        """
        Main file decompression function
        """
        with open(input_file, 'rb') as f:
            data = f.read()
        
        print(f"Input file size: {len(data)} bytes")
        
        if compression_type is None:
            compression_type = self.identify_compression_type(data)
            print(f"Detected compression type: {compression_type}")
        
        # Check header (first 8 bytes)
        header = data[:8]
        print(f"Header (hex): {' '.join(f'{b:02X}' for b in header)}")
        
        # Interpret header
        padding = struct.unpack('<I', header[:4])[0]  # little-endian
        compressed_size = struct.unpack('<I', header[4:8])[0]
        
        print(f"Padding: 0x{padding:08X} ({padding})")
        print(f"Compressed size: 0x{compressed_size:08X} ({compressed_size})")
        
        # Compressed data starts at offset 8
        compressed_data = data[8:8+compressed_size]
        
        # Select decompression method
        if compression_type == "LZXRLE":
            # First LZX decompression, then RLE
            print("Step 1: LZX decompression...")
            lzx_decompressed = self.decompress_lzx_xmem(compressed_data)
            print(f"After LZX: {len(lzx_decompressed)} bytes")
            
            print("Step 2: RLE decompression...")
            final_data = self.decompress_rle(lzx_decompressed)
            
        elif compression_type == "ZLIBRLE":
            # First ZLIB decompression, then RLE
            print("Step 1: ZLIB decompression...")
            zlib_decompressed = self.decompress_zlib(compressed_data)
            print(f"After ZLIB: {len(zlib_decompressed)} bytes")
            
            print("Step 2: RLE decompression...")
            final_data = self.decompress_rle(zlib_decompressed)
            
        elif compression_type == "PS3ZLIB":
            # PS3 ZLIB has its own format
            print("PS3 ZLIB decompression...")
            final_data = self.decompress_ps3_zlib(compressed_data)
            
        elif compression_type == "RLE" or compression_type == "None":
            # Only RLE or no compression
            print("RLE decompression...")
            final_data = self.decompress_rle(compressed_data)
            
        else:
            # Try everything sequentially
            print("Unknown type, trying different methods...")
            
            # Attempt 1: PS3 ZLIB
            try:
                final_data = self.decompress_ps3_zlib(compressed_data)
                print("✓ PS3 ZLIB works")
            except:
                # Attempt 2: ZLIB + RLE
                try:
                    zlib_decompressed = self.decompress_zlib(compressed_data)
                    final_data = self.decompress_rle(zlib_decompressed)
                    print("✓ ZLIB + RLE works")
                except:
                    # Attempt 3: Only RLE
                    try:
                        final_data = self.decompress_rle(compressed_data)
                        print("✓ Only RLE works")
                    except:
                        raise ValueError("Cannot decompress data")
        
        print(f"Decompressed size: {len(final_data)} bytes")
        
        # Save file
        with open(output_file, 'wb') as f:
            f.write(final_data)
        
        return len(final_data)


class DecompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MC_CLE Decompressor")
        self.root.geometry("700x500")
        
        self.decompressor = MC_CLE_Decompressor()
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.compression_type = tk.StringVar(value="AUTO")
        
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input file
        ttk.Label(main_frame, text="Input file:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_file, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.select_input).grid(row=0, column=2)
        
        # Output file
        ttk.Label(main_frame, text="Output file:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_file, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.select_output).grid(row=1, column=2)
        
        # Compression type
        ttk.Label(main_frame, text="Compression type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        type_combo = ttk.Combobox(main_frame, textvariable=self.compression_type, 
                                  values=["AUTO", "LZXRLE", "ZLIBRLE", "PS3ZLIB", "RLE", "None"],
                                  state="readonly", width=20)
        type_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Decompress button
        ttk.Button(main_frame, text="Decompress", command=self.decompress_file,
                  style="Accent.TButton").grid(row=3, column=0, columnspan=3, pady=20)
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="Format Information", padding="10")
        info_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        info_text = """
        File format (based on 4J Studios code):
        
        Offset 0x00: Padding (uint32_t)
        Offset 0x04: Compressed size (uint32_t)
        Offset 0x08: Compressed data
        
        Compression types:
        • LZXRLE: LZX + RLE (Xbox 360)
        • ZLIBRLE: ZLIB + RLE (PC, Xbox One, PS4, PS Vita)
        • PS3ZLIB: ZLIB with header (PS3)
        • RLE: Only RLE compression
        • None: No compression
        """
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).grid(row=0, column=0)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.log_text = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def select_input(self):
        filename = filedialog.askopenfilename(title="Select file to decompress")
        if filename:
            self.input_file.set(filename)
            base, ext = os.path.splitext(filename)
            self.output_file.set(f"{base}_decompressed{ext}")
    
    def select_output(self):
        filename = filedialog.asksaveasfilename(title="Save decompressed file as")
        if filename:
            self.output_file.set(filename)
    
    def decompress_file(self):
        if not self.input_file.get():
            messagebox.showerror("Error", "Select input file!")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Select output file!")
            return
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start decompression in separate thread
        thread = threading.Thread(target=self._decompress_thread)
        thread.daemon = True
        thread.start()
    
    def _decompress_thread(self):
        try:
            self.progress.start()
            self.log("Starting decompression...")
            
            comp_type = self.compression_type.get()
            if comp_type == "AUTO":
                comp_type = None
            
            # Read file to analyze header
            with open(self.input_file.get(), 'rb') as f:
                data = f.read(16)
            
            self.log(f"First 16 bytes: {' '.join(f'{b:02X}' for b in data)}")
            
            if len(data) >= 8:
                padding = struct.unpack('<I', data[:4])[0]
                comp_size = struct.unpack('<I', data[4:8])[0]
                self.log(f"Padding: 0x{padding:08X} ({padding})")
                self.log(f"Compressed size: 0x{comp_size:08X} ({comp_size})")
            
            output_size = self.decompressor.decompress_file(
                self.input_file.get(),
                self.output_file.get(),
                comp_type
            )
            
            self.progress.stop()
            self.log(f"\n✓ Success! Decompressed to {output_size} bytes")
            self.log(f"Saved as: {self.output_file.get()}")
            
            messagebox.showinfo("Success", 
                              f"File has been decompressed!\n"
                              f"Size: {output_size} bytes")
            
        except Exception as e:
            self.progress.stop()
            self.log(f"\n✗ Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during decompression:\n{str(e)}")


def main():
    root = tk.Tk()
    app = DecompressorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
