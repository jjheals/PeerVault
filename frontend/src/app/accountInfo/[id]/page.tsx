import React, {Suspense} from "react";
import { useParams } from "next/navigation";
import axios from "axios";
import Table from "@/app/table"
import { TableSkeleton } from "@/app/skeletons";


const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});



export default function Home({ params }: { params: { id: string; }; }) {  
  var user_list = [];
  // TODO --> get this to return and display SOMETHING
  function getSharedWithInfo() { 
    instance
    .get("ui/get-stored-with-info")
    .then(function (response){
      var peer_array = response["data"]
      var peer_names = []
      for(var i = 0; i < peer_array.length; i++){
        peer_names[i] = peer_array[i]["common_name"]
      }
      user_list= peer_names;
    })
    .catch (function (error) {
      console.log("errored:", error)
    });
  }


  // TODO -->
  /*
    - CREATE A DISPLAY TABLE FOR THE USER INFORMATION
      - Common-name, amount shared (bytes), amount stored remotely (bytes), amount stored locally (bytes), View more information button?

    - CREATE A FULL FLESHED OUT DISPLAY PAGE FOR THE LIST OF ALL ITEMS 


    -TABS:

    -
       */


  const common_name = params.id;
    return (
      <div>
        <div className="header">
          <div className="header-row">
            <div className="titleText">Account Info:{common_name}</div>
          </div>
        </div>


        <div>
          <div className = "subtitleText">Quick Facts</div>
          <div className = "table">
            <div className= "tr">
                <div className = "th">Total Amount Stored Locally:{}</div>
                <div className = "th">Total Amount Stored Remotely:{}</div>
                <div className = "th">Total Amount Shared:{}</div>
                <div className = "th">My MAC addr:{}</div>
                <div className = "th">My Current IP addr:{}</div>
            </div>
          </div>
        </div>


        <div>
          <div className = "subtitleText">History Summary:</div>
          <Suspense fallback={<TableSkeleton />}>
            <Table/>
          </Suspense>
        </div>

      </div>
    )
}