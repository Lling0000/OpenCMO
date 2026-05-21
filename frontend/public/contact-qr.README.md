The asset `contact-qr.png` is now the OpenCMO WeChat GROUP QR card (portrait,
dark background that already includes a title and the QR with quiet zone).

To swap it later, overwrite BOTH of these with the new exported PNG:
- `frontend/public/contact-qr.png`
- `assets/community-qr.png` (repo root, used by the READMEs)

The widget renders the card full-bleed and undistorted (`w-full h-auto`), so
export the new image at the same portrait aspect ratio. If you change the file
name, also update `QR_ASSET` in
`frontend/src/components/FloatingContactQR.tsx`.
