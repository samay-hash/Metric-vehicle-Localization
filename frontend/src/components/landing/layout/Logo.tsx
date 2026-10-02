import { cn } from "@/lib/utils";

type LogoProps = {
  href?: string;
  className?: string;
};

function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="-48 -72 700 700" aria-hidden="true" className={className}>
      <g transform="translate(-10.509 590.638) scale(0.1 -0.1)">
        <path
          fill="currentColor"
          d="M1981 5899 c-128 -16 -291 -81 -409 -161 -70 -47 -212 -194 -258 -268 -23 -36 -68 -112 -101 -170 -254 -440 -365 -630 -642 -1105 -174 -297 -337 -583 -363 -635 -134 -271 -137 -581 -8 -865 15 -33 130 -238 257 -455 126 -217 326 -561 443 -765 274 -474 395 -680 431 -730 54 -74 173 -186 260 -244 93 -63 200 -111 306 -138 l68 -18 1155 0 1155 0 82 22 c96 26 209 76 290 130 72 47 201 170 250 236 38 52 234 384 653 1107 141 245 294 508 340 585 46 77 100 169 121 204 48 80 93 203 115 312 22 111 15 320 -15 434 -31 116 -82 212 -412 775 -163 278 -396 681 -519 895 -251 438 -283 487 -382 586 -122 120 -263 200 -446 252 l-77 22 -1115 1 c-613 1 -1144 -2 -1179 -7z"
        />
        <path
          fill="#fff"
          d="M4445 4535 c101 -27 155 -84 176 -188 l11 -55 -22 -109 c-114 -557 -432 -1425 -771 -2103 -185 -370 -324 -588 -480 -755 -78 -82 -123 -107 -199 -107 -95 0 -168 51 -211 148 -10 23 -55 223 -99 445 l-81 404 -44 90 c-51 105 -106 174 -193 244 -112 90 -248 154 -682 323 -305 118 -466 188 -504 220 -47 38 -86 120 -86 177 1 93 51 164 173 244 376 247 1146 572 1872 792 396 120 912 240 1050 244 17 1 57 -6 90 -14z"
        />
      </g>
    </svg>
  );
}

export function Logo({ href = "#hero", className }: LogoProps) {
  return (
    <a
      href={href}
      className={cn(
        "inline-flex shrink-0 items-center gap-2.5 whitespace-nowrap font-sans text-sm leading-none font-medium",
        className,
      )}
    >
      <LogoMark className="size-10 shrink-0" />
      Roostr CV
    </a>
  );
}
