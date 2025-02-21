'use client';

import React from "react";
import { Model } from "@/model";
import { useRouter} from "next/navigation";

export default function Home() {
    const [model, setModel] = React.useState(new Model())
    const [redraw, forceRedraw] = React.useState(0);

    function refresh() {
        forceRedraw(redraw + 1);
    }

    const router = useRouter();

    return (
      <div className="header">
        <div className="header-row">
          <div className="titleText">Sign In</div>
          <div className="header-options-row">
            <button onClick={()=> router.push("/")}>
              <div className="header-button-text-option-one">Back</div>
            </button>
            <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>

          </div>
        </div>
      </div>
    )
}