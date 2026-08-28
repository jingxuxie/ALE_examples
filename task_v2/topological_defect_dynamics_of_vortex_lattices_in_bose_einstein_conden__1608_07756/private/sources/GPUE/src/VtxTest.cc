//
// Created by Lee James O'Riordan on 3/1/17.
//

#define NUM_VORT 3

#include "../include/vort.h"
#include <iostream>
#include <vector>
#include <algorithm>
#include <iterator>
#include <algorithm>
#include <cassert>
#include <random>

int main(){
    //########################################################################//

    int2 c = {1,2};
    double2 cD = {3.1,4.2};

    std::mt19937 rng(time(0));
    std::uniform_real_distribution<> dist(-0.1,0.1);

    //VtxList::VtxList()
    std::shared_ptr<Vtx::VtxList> vl = std::make_shared<Vtx::VtxList>(11);
    std::shared_ptr<Vtx::VtxList> vlp = std::make_shared<Vtx::VtxList>(11);

    //########################################################################//
    // Vortex::Vortex(int2 coords, double2 coordsD, int winding, int isOn, std::size_t timeStep)
    //########################################################################//
/*
    //Create UID -1 vortex, and check values
    std::shared_ptr<Vtx::Vortex> vtx = std::make_shared<Vtx::Vortex>(c,cD, 1, true, true, 0);

    assert( vtx->getUID() == -1 );
    assert( vtx->getCoords().x == 1 );
    assert( vtx->getCoordsD().y == 4.2 );
    assert( vtx->getWinding() == 1 );
    assert( vtx->getIsOn() == true );
    assert( vtx->getTimeStep() == 0 );
    std::cout << "Vortex value initialisation check passed"<<std::endl;

    //########################################################################//
    // VtxList::addVtx(std::shared_ptr<Vtx::Vortex> vtx)
    // VtxList::getVortices()
    //########################################################################//

    assert(vl->getVortices().size() == 0);
    vl->addVtx(vtx);
    assert(vl->getVortices().size() == 1);
    std::cout << "Vortex add to VtxList check passed"<<std::endl;

    //########################################################################//
    // VtxList::getVtx_Idx(std::size_t idx)
    //########################################################################//

    //Create 0-9 UID vortices
    for(int i =0; i < 10; ++i){
        c.x = i;
        c.y = i;
        cD.x =  i+dist(rng);
        cD.y =  i+dist(rng);
        vl->addVtx(std::make_shared<Vtx::Vortex>(c, cD, 1, true, false, 0));
    }

    for (int i = 0; i < vl->getVortices().size(); ++i){
        //std::cout << vl->getVtx_Idx(i)->getUID() << "\n";
        assert(vl->getVtx_Idx(i)->getUID() == -1);
    }
    std::cout << "Passed linear UID check passed"<<std::endl;

    //########################################################################//
    // VtxList::getVtxIdx_Uid(std::size_t uid)
    // VtxList::removeVtx(size_t idx)
    //########################################################################//

    vl->removeVtx(2);
    assert(vl->getVortices().size() == 10);
    std::cout << "Passed remove Idx 2 check passed"<<std::endl;

    //########################################################################//
    //
    //########################################################################//
    c.x++; c.y++; cD.x += 1.; cD.y += 1.;
    vl->addVtx(std::make_shared<Vtx::Vortex>(c,cD, -1, false, false, 1000));
    assert(vl->getVtx_Uid(-1)->getIsOn() == true);
    assert(vl->getVortices().size() == 11);
    std::cout << "Passed add new vortex with uid=suid++ (11), and getVtx_Uid"<<std::endl;

    //########################################################################//
    //########################################################################//

    assert(vl->getVtx_Idx(10)->getIsOn() == false);
    assert(vl->getVtx_Idx(10)->getWinding() == -1);
    assert(vl->getVtx_Idx(10)->getWinding() == -vl->getVtx_Uid(-1)->getWinding());
    std::cout << "Passed getVtx_Idx "<<std::endl;

    //########################################################################//
    // VtxList::addVtx(std::shared_ptr<Vtx::Vortex> vtx, std::size_t idx)
    //########################################################################//

    vl->addVtx(std::make_shared<Vtx::Vortex>(c,cD, 3, false, true, 1000),5);
    assert(vl->getVtx_Idx(5)->getIsOn() == false);
    assert(vl->getVtx_Idx(5)->getWinding() == 3);
    std::cout << (vl->getVtxIdx_Uid(12) == -1) << "\n";

    assert(vl->getVtxIdx_Uid(12) == -1);
    assert(vl->getVtx_Idx(11)->getWinding() == vl->getVtx_Uid(11)->getWinding());
    std::cout << "Passed addVtx at arbitrary position "<<std::endl;

    //########################################################################//
    // VtxList::getMax_Uid()
    //########################################################################//
    //Value is post-incremented, so will always be +1 higher than largest UID stored

    assert(vl->getMax_Uid() == 12);
    std::cout << "Passed max UID check "<<std::endl;

    //########################################################################//
    // swapUid(std::shared_ptr<Vtx::Vortex> v1, std::shared_ptr<Vtx::Vortex> v2)
    //########################################################################//
    assert(vl->getVtx_Uid(6)->getUID() == vl->getVtx_Idx(6)->getUID());
    vl->swapUid(vl->getVtx_Uid(6),vl->getVtx_Uid(10));
    assert(vl->getVtx_Uid(10)->getUID() == vl->getVtx_Idx(6)->getUID());
    std::cout << "Passed swap UID check 1"<<std::endl;

    //########################################################################//
    // swapUid_Idx(std::size_t idx0, std::size_t idx1)
    //########################################################################//
    assert(vl->getVtx_Uid(6)->getUID() == vl->getVtx_Idx(10)->getUID());
    vl->swapUid_Idx(vl->getVtxIdx_Uid(6),vl->getVtxIdx_Uid(10));
    assert(vl->getVtx_Uid(6)->getUID() == vl->getVtx_Idx(6)->getUID());
    std::cout << "Passed swap UID check 2"<<std::endl;

    //########################################################################//
    // VtxList::getVtxMinDist(std::shared_ptr<Vortex> vtx)
    //########################################################################//
    assert(vl->getVtxMinDist(vl->getVtx_Uid(8))->getUID() == 9 || vl->getVtxMinDist(vl->getVtx_Uid(8))->getUID() == 7);
    std::cout << "Passed getVtxMinDist check (even if it isn't full rigorous) "<<std::endl;

    //########################################################################//
    // VtxList::sortVortices()
    //########################################################################//
    assert( vl->getVtx_Idx(6)->getUID() == 6 );
    vl->sortVtxUID();
    assert( vl->getVtx_Idx(6)->getUID() == 7 );
    std::cout << "Passed sortVortices check"<<std::endl;

*/
    //########################################################################//
    //########################################################################//


    std::cout << "Resetting current and previous list for testing"<<std::endl;

    vl.reset(); vl = std::make_shared<Vtx::VtxList>(8);
    vlp.reset(); vlp = std::make_shared<Vtx::VtxList>(8);

    //########################################################################//
    // Populate vortex arrays
    //########################################################################//
    //Vtx::Vortex::resetSUID();
    for( int i = 0; i < 2; ++i ){
        c.x = i;
        c.y = i;
        cD.x =  i+dist(rng);
        cD.y =  i+dist(rng);
        vlp->addVtx(std::make_shared<Vtx::Vortex>(c, cD, 1, true, 0));
        vlp->getVtx_Idx(i)->updateUID(vlp->getMax_Uid());
    }

    c.x = 12;
    c.y = 16;
    cD.x =  12+dist(rng);
    cD.y =  16+dist(rng);
    vlp->addVtx(std::make_shared<Vtx::Vortex>(c, cD, 1, true, 0));
    vlp->getVtx_Idx(2)->updateUID(vlp->getMax_Uid());

    for( int i = 3; i < 5; ++i ){
        c.x = i;
        c.y = i;
        cD.x =  i+dist(rng);
        cD.y =  i+dist(rng);
        vlp->addVtx(std::make_shared<Vtx::Vortex>(c, cD, 1, true, 0));
        vlp->getVtx_Idx(i)->updateUID(vlp->getMax_Uid());
    }
    int loop=1;
test:
    if (loop==2)
        exit(0);
    int size=6;
    for( int i = size; i >= 0; --i ){
        c.x = i*loop;
        c.y = i*loop;
        cD.x =  i*loop+dist(rng);
        cD.y =  i*loop+dist(rng);
        auto v = std::make_shared<Vtx::Vortex>(c, cD, 1, false, 0);
        vl->addVtx(v);
    }

    for(auto a: vlp->getVortices())
        std::cout << a->getUID() << "\n";
    //########################################################################//
    // VtxList::minDistPair(std::shared_ptr<Vortex> vtx, double minRange)
    // This entire section would be more efficiently implemented by unioning
    // the two lists, and then selecting behaviour based upon the required
    // operations. But, that is more effort right now than it is worth...
    //########################################################################//
    for (auto vtxPrev : vlp->getVortices()) {
        auto vtxMin = vl->minDistPair(vtxPrev, 1);
        if (vtxMin.second != nullptr && vtxMin.second->getUID() < 0 ) {
            vtxMin.second->updateUID(vtxPrev->getUID());
            vtxMin.second->updateIsOn(true);
            std::cout << "UIDc=" << vtxMin.second->getUID() << " UIDp=" << vtxPrev->getUID() << "\n";
        }
        else{
            vtxPrev->updateIsOn(false);
            vl->addVtx(vtxPrev);
            std::cout << "No min found for UID=" << vtxPrev->getUID() << " X,Y="<< vtxPrev->getCoordsD().x << "," << vtxPrev->getCoordsD().y <<"\n";
        }
    }
    std::cout << "\n";
    int count=0;
    for (auto v: vl->getVortices()) {
        count ++;
        if (!(v->getUID() < 0))
            std::cout << "ON:="<< v->getIsOn() << " UIDc:=" << v->getUID()<< "\n";
        else {
            std::cout << "Index=" << count << " added to list with UID="<< vl->getMax_Uid() <<"\n";
            v->updateUID(vl->getMax_Uid()++);
            v->updateIsOn(true);
            std::cout << "ON:="<< v->getIsOn() << " UIDc:=" << v->getUID()<< "\n";
        }
    }
    //vl->arrangeVtx(vlp->getVortices());
    std::sort(vl->getVortices().begin(), vl->getVortices().end(), [](std::shared_ptr<Vtx::Vortex> a, std::shared_ptr<Vtx::Vortex> b) {
        return b->getUID() < a->getUID();
    });
    vlp->getVortices().swap(vl->getVortices());
    loop++;
    goto test;



//nvcc -g -G ./vort.cc -o vort.o -std=c++11 -c -Wno-deprecated-gpu-targets; nvcc -g -G ./VtxTest.cc -std=c++11 -o VtxTest.o -c -Wno-deprecated-gpu-targets; nvcc vort.o VtxTest.o -Wno-deprecated-gpu-targets; ./a.out
    return 0;
}
