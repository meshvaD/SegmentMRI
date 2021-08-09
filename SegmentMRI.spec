# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['SegmentMRI\\SegmentMRI.py'],
             pathex=['C:\\Users\\HS student\\source\\repos\\SegmentMRI'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

a.datas.append(('hand.png', 'C:\\Users\\HS student\\source\\repos\\SegmentMRI\\SegmentMRI\\hand.png', 'Data'))

a.datas.append(('zoom_in.png', 'C:\\Users\\HS student\\source\\repos\\SegmentMRI\\SegmentMRI\\zoom_in.png', 'Data'))

a.datas.append(('zoom_out.png', 'C:\\Users\\HS student\\source\\repos\\SegmentMRI\\SegmentMRI\\zoom_out.png', 'Data'))


exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='SegmentMRI',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
